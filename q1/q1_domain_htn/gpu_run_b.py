"""Extractor B runner on the rented GPU (addendum HTN v3, Sections 5.3, 5.5, 15). Sends each rendered message once to
the local vLLM server (OpenAI chat completions), sequentially: 18 gate chunks, then 5 HTN chunks, then the test-retest
chunk(s) as run 2. One retry only for a technical failure (no response, HTTP error, timeout, empty text). A returned
response (also truncated or unparseable) is never re-requested. Every attempt saved with time, finish_reason, usage and
SHA-256. Usage: python3 run_b.py <bundle_dir> <out_dir>"""
import hashlib
import json
import os
import sys
import time
import urllib.request

B, O = sys.argv[1], sys.argv[2]
URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "Qwen/Qwen2.5-72B-Instruct-AWQ"
REQ = {"temperature": 0, "top_p": 1.0, "top_k": -1, "repetition_penalty": 1.0, "seed": 42, "max_tokens": 4096}
SYSTEM = open(os.path.join(B, "system_v2.txt"), encoding="utf-8").read()
plan = json.load(open(os.path.join(B, "plan.json"), encoding="utf-8"))


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def call(user):
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], **REQ}
    r = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=1800) as resp:
        return json.loads(resp.read())


for item in plan:
    phase, cid, run = item["phase"], item["chunk_id"], item["run"]
    d = os.path.join(O, phase)
    os.makedirs(d, exist_ok=True)
    stem = cid if run == 1 else f"{cid}_run{run}"
    if os.path.exists(os.path.join(d, stem + ".json")):
        continue  # already returned: never re-requested
    user = open(os.path.join(B, item["file"]), encoding="utf-8").read()
    attempts = []
    for att in (1, 2):
        t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        try:
            resp = call(user)
            ch = resp["choices"][0]
            text = ch["message"]["content"] or ""
            rec = {"attempt": att, "started": t0, "ended": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "finish_reason": ch.get("finish_reason"), "usage": resp.get("usage"), "response_id": resp.get("id"),
                   "text_sha256": sha(text)}
            attempts.append(rec)
            if text.strip():
                out = {"chunk_id": cid, "phase": phase, "run": run, "user_sha256": sha(user), "system_sha256": sha(SYSTEM),
                       "request": REQ, "model": MODEL, "attempts": attempts, "finish_reason": ch.get("finish_reason"),
                       "usage": resp.get("usage"), "text": text}
                open(os.path.join(d, stem + ".txt"), "w", encoding="utf-8", newline="\n").write(text)
                json.dump(out, open(os.path.join(d, stem + ".json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
                print(phase, stem, ch.get("finish_reason"), resp.get("usage"), flush=True)
                break
            rec["failure"] = "empty response"
        except Exception as e:  # technical failure
            attempts.append({"attempt": att, "started": t0, "ended": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             "failure": repr(e)[:500]})
        print(phase, stem, "technical failure attempt", att, attempts[-1].get("failure"), flush=True)
    else:
        json.dump({"chunk_id": cid, "phase": phase, "run": run, "attempts": attempts, "returned": False},
                  open(os.path.join(d, stem + ".failed.json"), "w", encoding="utf-8"), indent=1)
print("ALL DONE", flush=True)
