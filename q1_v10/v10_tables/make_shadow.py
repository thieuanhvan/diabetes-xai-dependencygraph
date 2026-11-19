"""Build the v10 shadow: a copy of P7's analysis tools that reads P5 frames and writes under p5_v10/outputs.

Nothing outside p5_v10/ is written. P7's tools (D:/evisyn/projects/diabetesxai/paper7/tools) are copied to
p5_v10/tools_v10 with these text substitutions only:
  - the P7 outputs root  ->  p5_v10/outputs (all spellings used in the tools);
  - BRFSS 2021 input     ->  frames/brfss2021_p5.csv (P5 0.2.1, Kaggle coding, Sex = SEXVAR);
  - NHANES diabetes input (Table 4) -> frames/t4_<cycle>_p5.csv;
  - the analytic-frame hashes of the CKD and HTN domains -> the hashes of the P5 frames.
The shadow outputs root receives the data-independent inputs of v9 (role tables, lock sets, frozen extraction and
graph files, unit-test records), the P5 frames at the paths the tools read, and the NHIS result files of v9 (NHIS is
not in P5; its inputs and code are unchanged). Results of the 0.2.0 measurement run whose input frame is byte-identical
under 0.2.1 (frame_manifest.json) are copied from p5_migration/p5 instead of being recomputed.
Usage: python -I make_shadow.py   (idempotent for the copies; refuses to overwrite an existing results file)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
TOOLS = Path("D:/evisyn/projects/diabetesxai/paper7/tools")
T10 = HERE / "tools_v10"
O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
O10 = HERE / "outputs"
MIG = O / "p5_migration" / "p5"
FR = HERE / "frames"
SKIP_DIRS = {"killtest_x1", "killtest_x5", "overlap", "__pycache__"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rewrite(src: str) -> str:
    s = src
    s = re.sub(r'D:/20-study/uit/research/diabetesxai/paper7/outputs(?!/p5_v10)',
               'D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs', s)
    s = re.sub(r'D:\\20-study\\uit\\research\\diabetesxai\\paper7\\outputs(?!\\p5_v10)',
               r'D:\\20-study\\uit\\research\\diabetesxai\\paper7\\outputs\\p5_v10\\outputs', s)
    s = re.sub(r'PAPER7 / "outputs"(?! / "p5_v10")', 'PAPER7 / "outputs" / "p5_v10" / "outputs"', s)
    s = s.replace('H / "outputs/crossdataset_p4/results"', 'H / "outputs/p5_v10/outputs/crossdataset_p4/results"')
    s = s.replace('P4 / "data" / "cdc_brfss_diabetes_2021.csv"',
                  'Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/frames/brfss2021_p5.csv")')
    s = s.replace('f"C:/Repos/uit/nhanes-diabetes/outputs/tabular/cdc_nhanes_diabetes_{cyc}.csv"',
                  'f"D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/frames/t4_{cyc}_p5.csv"')
    return s


def copy_tools():
    n = 0
    for p in TOOLS.rglob("*"):
        rel = p.relative_to(TOOLS)
        if any(part in SKIP_DIRS for part in rel.parts) or p.is_dir():
            continue
        dst = T10 / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # vendored CARLA files are hash-checked byte for byte (b_vendor.verify): never re-encode them; any .py the
        # rewrite leaves unchanged is also copied byte for byte (fix 18/11 17:07, after b_models_mlp/b_ar failed)
        s0 = p.read_text(encoding="utf-8") if p.suffix == ".py" else None
        if p.suffix == ".py" and "vendor" not in rel.parts and rewrite(s0) != s0:
            dst.write_text(rewrite(s0), encoding="utf-8", newline="\n")
            n += 1
        else:
            shutil.copyfile(p, dst)
    # analytic-frame hashes of the two NHANES domains
    for f, frame in ((T10 / "q1_domain_ckd" / "a2_domain.py", FR / "ckd_p5.csv"),
                     (T10 / "q1_domain_htn" / "a2_domain_htn.py", FR / "htn_ext_p5.csv")):
        s = f.read_text(encoding="utf-8")
        s = re.sub(r'ANALYTIC_SHA256 = "[0-9a-f]{64}"', f'ANALYTIC_SHA256 = "{sha(frame)}"', s)
        f.write_text(s, encoding="utf-8", newline="\n")
    return n


def cp(src: Path, dst: Path):
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                cp(p, dst / p.relative_to(src))
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        assert sha(dst) == sha(src), f"refusing to overwrite a different file: {dst}"
        return
    shutil.copyfile(src, dst)


def main():
    log = {"tools_py_rewritten": copy_tools()}
    # data-independent inputs of v9
    for d in ("a0_freeze", "a0_role_table", "a1_extraction", "a1_extractor1_claude"):
        cp(O / "q1_domain_ckd" / d, O10 / "q1_domain_ckd" / d)
    for d in ("a0_freeze", "a0_role_table", "a1_extraction"):
        cp(O / "q1_domain_htn" / d, O10 / "q1_domain_htn" / d)
    cp(O / "q1_ext_b" / "unit_tests", O10 / "q1_ext_b" / "unit_tests")
    for f in ("dm_role_table.csv", "dm_lock_set.txt"):
        cp(O / "q1_posthoc_v5" / "nhanes_dm" / f, O10 / "q1_posthoc_v5" / "nhanes_dm" / f)
    for p in (O / "q1_posthoc_s_p6").glob("*.py"):
        cp(p, O10 / "q1_posthoc_s_p6" / p.name)
    # P5 frames at the paths the tools read
    cp(FR / "ckd_p5.csv", O10 / "q1_domain_ckd" / "a0_nhanes_ckd" / "nhanes_ckd_analytic_2017-2023.csv")
    cp(FR / "htn_ext_p5.csv", O10 / "q1_domain_htn" / "a0_nhanes_htn" / "nhanes_htn_analytic_2017-2023.csv")
    cp(FR / "dm_p5.csv", O10 / "q1_posthoc_v5" / "nhanes_dm" / "nhanes_dm_rows_2017-2023.csv")
    nd = O10 / "q1_posthoc_v5" / "nhanes_dm"
    (nd / "a0_dm.json").write_text(json.dumps({
        "statement": "v10 copy: rows from p7_from_p5.py (P5 0.2.1), role table and lock set copied from the v9 run "
                     "(role derivation does not read the data)",
        "rows_csv_sha256": sha(nd / "nhanes_dm_rows_2017-2023.csv"), "role_table_sha256": sha(nd / "dm_role_table.csv"),
        "lock_set_sha256": sha(nd / "dm_lock_set.txt")}, indent=2) + "\n", encoding="utf-8")
    # NHIS result files of v9 (not in P5: unchanged inputs, unchanged code)
    nhis = [p for p in (O / "crossdataset_p4" / "results").glob("*nhis*") if p.is_file()]
    for p in nhis:
        cp(p, O10 / "crossdataset_p4" / "results" / p.name)
    log["nhis_files_copied"] = len(nhis)
    # results of the 0.2.0 measurement run whose frames are byte-identical under 0.2.1
    man = json.loads((HERE / "frame_manifest.json").read_text(encoding="utf-8"))
    assert all(man["identical_to_0_2_0_frame"][k] for k in ("ckd", "dm", "t4_2017-2020", "t4_2021-2023"))
    reuse = [("q1_domain_ckd/a2_model", None), ("q1_domain_ckd/a2_runs_main", None), ("q1_domain_ckd/a2_analysis", None),
             ("q1_posthoc_ses_splits/ses_freeze", None), ("q1_posthoc_v5/nhanes_dm/runs_dm_a1c", None),
             ("q1_posthoc_v5/nhanes_dm/runs_dm_diag", None), ("q1_posthoc_v5/nhanes_dm/runs_dm_hbp_measured", None)]
    for rel, _ in reuse:
        cp(MIG / rel, O10 / rel)
    t4 = [p for p in (MIG / "crossdataset_p4" / "results").glob("cross_nhanes*") if p.is_file()]
    for p in t4:
        cp(p, O10 / "crossdataset_p4" / "results" / p.name)
    log["reused_from_measurement_run"] = [r for r, _ in reuse] + [f"crossdataset_p4/results ({len(t4)} NHANES _v3 files)"]
    (HERE / "shadow_manifest.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
