"""Extension B models on BRFSS 2021 diabetes (prereg v3 5.5, 4.6, 5.2 "Model identity").

  --model mlp   CARLA ANN architecture (vendored AnnModel): hidden 18, 9, 3, ReLU, softmax output; Adam lr 0.002,
                batch 1,024, 20 epochs, torch seed 42 (DataLoader shuffle generator seeded 42), BCE on the softmax
                output against one-hot labels (CARLA's training loss); inputs = P4-range scaled features.
  --model lr    P7 configuration (p7_cross_classifiers.py): StandardScaler + LogisticRegression(max_iter 5000,
                random_state 42) on the raw features.
  --model xgb   P4 configuration (configs/default.yaml, threads unchanged) through P7's train_xgb. Identity with
                the P4/P7 model is checked: test AUC to 4 decimals and eligible count equal P7's BRFSS run, and P7's
                exhaustive search on the first 10 cohort patients returns the change sets of
                cross_brfss2021_exh_changes.csv (published mode).
Writes outputs/q1_ext_b/models/<model>/: the model, test probabilities, cohort (test positions, P7 rule) and info.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import b_common as C  # noqa: E402

MLP = {"hidden": [18, 9, 3], "lr": 0.002, "batch": 1024, "epochs": 20, "seed": 42}


def train_mlp(Str, ytr):
    import torch
    import b_vendor as V
    torch.set_num_threads(2)
    Ann = V.carla_ann()
    torch.manual_seed(MLP["seed"])
    m = Ann(Str.shape[1], MLP["hidden"], 2)
    opt = torch.optim.Adam(m.parameters(), lr=MLP["lr"])
    X = torch.from_numpy(np.asarray(Str, np.float32))
    Y = torch.nn.functional.one_hot(torch.from_numpy(np.asarray(ytr, np.int64)), 2).float()
    ds = torch.utils.data.TensorDataset(X, Y)
    gen = torch.Generator().manual_seed(MLP["seed"])
    dl = torch.utils.data.DataLoader(ds, batch_size=MLP["batch"], shuffle=True, generator=gen)
    crit = torch.nn.BCELoss()
    hist = []
    for e in range(MLP["epochs"]):
        tot = 0.0
        m.train()
        for xb, yb in dl:
            opt.zero_grad()
            loss = crit(m(xb), yb)
            loss.backward()
            opt.step()
            tot += float(loss) * len(xb)
        hist.append(tot / len(ds))
    m.eval()
    return m, hist


def mlp_proba1(m, S):
    import torch
    with torch.no_grad():
        return m(torch.from_numpy(np.asarray(S, np.float32))).numpy()[:, 1].astype(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["mlp", "lr", "xgb"], required=True)
    a = ap.parse_args()
    C.check_prereg()
    C.below_normal()
    t0 = time.time()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    out = C.OUT / "models" / a.model
    out.mkdir(parents=True, exist_ok=True)
    from sklearn.metrics import roc_auc_score
    info = {"model": a.model, "n": len(X), "n_train": len(Xtr), "n_test": len(Xte), "features": cols,
            "p4_lo": lo.tolist(), "p4_span": span.tolist()}
    if a.model == "mlp":
        import torch
        m, hist = train_mlp(C.to_scaled(Xtr.to_numpy(), lo, span), ytr.to_numpy())
        proba = mlp_proba1(m, C.to_scaled(Xte.to_numpy(), lo, span))
        torch.save(m.state_dict(), out / "mlp_state_dict.pt")
        info.update(config=MLP, train_loss_per_epoch=hist)
    elif a.model == "lr":
        P = C.p7()  # noqa: F841 (taxonomy import side effects identical to P7)
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        m = Pipeline([("scale", StandardScaler()), ("lr", LogisticRegression(max_iter=5000, random_state=42))])
        m.fit(Xtr, ytr)
        proba = m.predict_proba(Xte)[:, 1]
        with open(out / "lr_pipeline.pkl", "wb") as fh:
            pickle.dump(m, fh)
        info.update(config="StandardScaler + LogisticRegression(max_iter=5000, random_state=42), P7")
    else:
        P = C.p7()
        P.seed_everything(P.CFG["random"]["seed"])
        res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**P.CFG["xgboost"]))
        m, proba = res["model"], np.asarray(res["proba"])
        m.save_model(str(out / "xgb_model.json"))
        info.update(config=P.CFG["xgboost"])
    auc = float(roc_auc_score(yte, proba))
    idx = C.cohort(proba)
    info.update(test_auc=auc, eligible_p_ge_0_5=int((proba >= 0.5).sum()), cohort_n=len(idx),
                cohort_min_p=float(proba[idx].min()), secs=time.time() - t0)
    pd.DataFrame({"test_pos": np.arange(len(Xte)), "test_index": Xte.index, "proba1": proba}).to_csv(
        out / "test_proba.csv", index=False)
    pd.DataFrame({"pid": np.arange(len(idx)), "test_pos": idx, "test_index": Xte.index[idx], "proba1": proba[idx]}).to_csv(
        out / "cohort.csv", index=False)
    if a.model == "xgb":
        ok_auc = f"{auc:.4f}" == "0.8233" and info["eligible_p_ge_0_5"] == 1798
        import p7_cross_exhaustive as E
        ref = pd.read_csv(C.PAPER7 / "outputs" / "crossdataset_p4" / "results" / "cross_brfss2021_exh_changes.csv")
        ref = ref[(ref["mode"] == "published") & (ref["pid"] < 10)].fillna({"changed": ""})
        queries = Xte.iloc[idx].reset_index(drop=True)
        mism = 0
        for i in range(10):
            got = [";".join(S) for S, k, d in E.search(m, queries.iloc[i], cols, "published")]
            exp = ref[ref["pid"] == i]["changed"].tolist()
            mism += got != exp
        info["identity_check"] = {"auc_and_eligible_equal_P7": ok_auc, "exhaustive_first10_mismatches": mism,
                                  "identical": bool(ok_auc and mism == 0)}
        if not info["identity_check"]["identical"]:
            print("XGBoost identity check FAILED", info["identity_check"], flush=True)
    C.write_json(out / "model_info.json", info)
    print(json.dumps({k: info[k] for k in ("model", "test_auc", "eligible_p_ge_0_5", "cohort_n", "cohort_min_p")}),
          flush=True)


if __name__ == "__main__":
    main()
