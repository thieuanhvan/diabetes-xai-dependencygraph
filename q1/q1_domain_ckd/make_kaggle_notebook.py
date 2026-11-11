"""Write the Kaggle notebook that runs extractor 2 (Qwen2.5-7B Q4_K_M, llama.cpp b12283 CUDA) on the frozen chunks.

Output: paper7/kaggle/p7_qwen_extraction.ipynb. Straight top-to-bottom; the student presses Run All.
Usage: python -I make_kaggle_notebook.py
"""
from __future__ import annotations

import json

from q1_common import PAPER7

CELLS = [
    ("# Locate the attached private dataset and set paths",
     r'''import glob, hashlib, json, os, subprocess, sys, time, zipfile, platform, urllib.request
from pathlib import Path
hits = glob.glob("/kaggle/input/**/inputs_manifest_sha256.txt", recursive=True)
assert len(hits) == 1, f"attach exactly one copy of the p7 inputs dataset, found {hits}"
IN = Path(hits[0]).parent
WORK = Path("/kaggle/working"); OUTD = WORK / "p7_qwen_outputs"; (OUTD / "raw").mkdir(parents=True, exist_ok=True)
SETT = json.loads((IN / "extraction_settings_v1.json").read_text(encoding="utf-8"))
X2 = SETT["extractor_2"]
print(IN)'''),
    ("# Verify the SHA-256 of every input file against the frozen manifest",
     r'''def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
bad = []
for line in (IN / "inputs_manifest_sha256.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"): continue
    h, name = line.split(None, 1); name = name.lstrip("*")
    if sha(IN / name) != h: bad.append(name)
assert not bad, f"hash mismatch: {bad}"
print("all inputs verified")'''),
    ("# Record GPU, driver and CUDA versions",
     r'''gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
nvcc = subprocess.run(["nvcc", "--version"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
print(gpu); print(nvcc)'''),
    ("# Build llama.cpp at tag b12283 with CUDA (about 10-15 minutes)",
     r'''os.chdir(WORK)
if not Path("llama.cpp").exists():
    subprocess.run(["git", "clone", "--depth", "1", "--branch", "b12283", "https://github.com/ggml-org/llama.cpp"], check=True)
commit = subprocess.run(["git", "-C", "llama.cpp", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
assert commit.startswith("f3b407ca1"), f"unexpected llama.cpp commit {commit}"
subprocess.run(["cmake", "-S", "llama.cpp", "-B", "llama.cpp/build", "-DGGML_CUDA=ON", "-DCMAKE_CUDA_ARCHITECTURES=75",
                "-DLLAMA_CURL=OFF", "-DCMAKE_BUILD_TYPE=Release"], check=True)
subprocess.run(["cmake", "--build", "llama.cpp/build", "--target", "llama-server", "-j", str(os.cpu_count())], check=True)
SERVER = WORK / "llama.cpp/build/bin/llama-server"
ver = subprocess.run([str(SERVER), "--version"], capture_output=True, text=True)
print(commit); print(ver.stdout + ver.stderr)'''),
    ("# Download the two GGUF files from Hugging Face and verify their SHA-256",
     r'''from huggingface_hub import hf_hub_download
MD = WORK / "model"; MD.mkdir(exist_ok=True)
for fn, h in X2["model_files"].items():
    p = Path(hf_hub_download(X2["model_repo"], fn, local_dir=str(MD)))
    assert sha(p) == h, f"GGUF hash mismatch for {fn}"
MODEL = MD / sorted(X2["model_files"])[0]
print("model verified", MODEL)'''),
    ("# Start llama-server with the frozen settings and wait until it is ready",
     r'''a = X2["server_args"]
srv = subprocess.Popen([str(SERVER), "-m", str(MODEL), "-c", str(a["ctx_size"]), "-np", str(a["parallel"]),
                        "-ngl", str(a["n_gpu_layers"]), "-s", str(a["seed"]), "-fa", a["flash_attn"],
                        "--host", "127.0.0.1", "--port", "8089", "--no-webui"],
                       stdout=open(OUTD / "server.log", "w"), stderr=subprocess.STDOUT)
def post(path, body, timeout=3600):
    r = urllib.request.Request("http://127.0.0.1:8089" + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as f: return json.loads(f.read())
for _ in range(600):
    try:
        urllib.request.urlopen("http://127.0.0.1:8089/health", timeout=5); break
    except Exception: time.sleep(2)
print("server ready")'''),
    ("# Run every chunk (recall-gate documents first, then KDIGO) and save raw outputs",
     r'''import csv
rows = list(csv.DictReader(open(IN / "chunk_index.csv", encoding="utf-8")))
rows.sort(key=lambda r: (0 if r["document"] != "kdigo" else 1, r["chunk_id"]))
req = dict(X2["request"]); req["json_schema"] = SETT[req["json_schema"]]
runlog = []
for r in rows:
    prompt = (IN / "prompts" / f"{r['chunk_id']}_chatml.txt").read_text(encoding="utf-8")
    ntok = len(post("/tokenize", {"content": prompt, "add_special": False})["tokens"])
    body = dict(req); body["prompt"] = prompt
    t0 = time.time(); res = post("/completion", body); dt = time.time() - t0
    (OUTD / "raw" / f"{r['chunk_id']}.txt").write_text(res["content"], encoding="utf-8")
    (OUTD / "raw" / f"{r['chunk_id']}_response.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    runlog.append({"chunk_id": r["chunk_id"], "prompt_tokens_server": ntok, "prompt_tokens_frozen": int(r["prompt_tokens"]),
                   "tokens_predicted": res.get("tokens_predicted"), "stop_type": res.get("stop_type"), "seconds": round(dt, 1),
                   "timings": res.get("timings"), "sha256_output": sha(OUTD / "raw" / f"{r['chunk_id']}.txt")})
    print(r["chunk_id"], ntok, res.get("tokens_predicted"), round(dt, 1), "s")
srv.terminate()'''),
    ("# Write the run manifest and zip everything into /kaggle/working",
     r'''man = {"gpu": gpu, "nvcc": nvcc, "llama_cpp_tag": "b12283", "llama_cpp_commit": commit, "server_version": (ver.stdout + ver.stderr).strip(),
       "model_files": X2["model_files"], "settings_sha256": sha(IN / "extraction_settings_v1.json"),
       "inputs_manifest_sha256": sha(IN / "inputs_manifest_sha256.txt"), "python": platform.python_version(),
       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "chunks": runlog}
(OUTD / "run_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
lines = [f"{sha(p)} *{p.relative_to(OUTD).as_posix()}" for p in sorted(OUTD.rglob("*")) if p.is_file() and p.name != "outputs_sha256.txt"]
(OUTD / "outputs_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
ZIP = WORK / "p7_qwen_outputs.zip"
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUTD.rglob("*")):
        if p.is_file(): z.write(p, p.relative_to(OUTD).as_posix())
print(ZIP, sha(ZIP))'''),
]


def main():
    cells = []
    for comment, code in CELLS:
        src = comment + "\n" + code
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                      "source": [l + "\n" for l in src.split("\n")[:-1]] + [src.split("\n")[-1]]})
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"},
                                       "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True}},
          "nbformat": 4, "nbformat_minor": 5}
    out = PAPER7 / "kaggle" / "p7_qwen_extraction.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main()
