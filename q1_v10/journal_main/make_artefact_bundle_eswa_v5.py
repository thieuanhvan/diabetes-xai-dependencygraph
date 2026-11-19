"""Anonymised artefact bundle for the ESWA submission (v5). Not part of the public repository.

Built like make_artefact_bundle_eswa.py (v4), with a token-safe redaction list written for v5:
- project codes are replaced only as whole tokens: "P4" -> "the taxonomy study" but "S-P4", "B-P1" stay;
- references to internal reviews of manuscript drafts become "an internal pre-submission review", review file
  paths and names are removed, "coordinator" becomes "the authors", journal names and draft numbers are removed,
  notebook-service names are neutralised, and quoted approvals in Vietnamese are removed;
- prereg file names are mapped to the reviewer-copy names.
Adds the S-P5 plan and the q1_posthoc_v5 code. The superseded file outputs/crossdataset_p4/cross_dataset_bootstrap.csv
(an early NHANES HbA1c run, n = 67) is not part of the bundle; README says so.
After redaction every text file is scanned for author names, project codes, paths, review references and Vietnamese
letters (kg/ excepted for the MoH quotations); a hit stops the script.

Usage: python -I make_artefact_bundle_eswa_v5.py
Output: paper7/submission/2-eswa/artefacts/ (kg, sparql, code, reviewer_copies, README.md, SHA256SUMS.txt)
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

TOOLS = Path("D:/evisyn/projects/diabetesxai/paper7/tools")
sys.path.insert(0, str(TOOLS / "journal_main"))
import make_artefact_bundle_eswa as V4  # noqa: E402  (KG_FILES, SPARQL queries, README base)

P7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
OUT = P7 / "submission" / "2-eswa" / "artefacts"
REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
VI = "ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ"
VIET = re.compile(f"[{VI}]", re.I)

PREREG = {"prereg_q1_extension_en_v3_20261111_1645.md": "preregistration_reviewer_copy.md",
          "prereg_addendum_htn_en_v3_20261112_0840.md": "preregistration_addendum_hypertension_reviewer_copy.md",
          "posthoc_b_mlp_plan_en_v1_20261112_0520.md": "posthoc_plan_network_seeds_reviewer_copy.md",
          "posthoc_ses_freeze_plan_en_v1_20261112_0726.md": "posthoc_plan_ses_splits_ar_reviewer_copy.md",
          "posthoc_forced_lever_plan_en_v1_20261112_0957.md": "posthoc_plan_forced_lever_reviewer_copy.md",
          "posthoc_v5_plan_en_v1_20261112_1211.md": "posthoc_plan_diagnosis_flags_levers_matched_reviewer_copy.md",
          "deviations_log_q1_en.md": "deviation_log_reviewer_copy.md"}

NS_OLD = "https://github.com/thieuanhvan/diabetes-xai-dependencygraph/kg#"
NS_NEW = "https://example.org/anonymised-review/kg#"
T = r"(?<![\w-])"   # token start: not after a letter, digit, underscore or hyphen
E = r"(?![\w-])"    # token end

# Applied to every file (kg, code, reviewer copies), in order.
SUBS_ALL = [
    (re.escape(NS_OLD), NS_NEW),
    (r"[A-Z]:/[^\s`|),;\"']*", "<local path>"),
    (r"https?://github\.com/[^\s`|)\"']*", "<repository URL withheld for review>"),
    (r"for Van Thieu", "for the authors"),
    (r"Van Thieu|Thieu Anh Van|Phuc Do", "the authors"),
    (r"[Aa]nh V[âa]n", "the authors"),
    (r"\b[Aa]pproved by the student\b", "approved by the authors"),
    (r"the student's own judgement", "the authors' own judgement"),
    (r"that decision is the student's", "that decision is the authors'"),
    (r"by a student at a public university", "by researchers at a public university"),
    (r"student decision", "author decision"),
    (r"student_hard_cap_usd", "hard_cap_usd"),
    (r"\b[Tt]he student\b", "the authors"),
    (r"\bstudent\b", "author"),
    (r"P7 HISS manuscript v6", "an earlier draft"),
    (r"HISS v6 content", "content of an earlier draft"),
    (r"\bHISS\b", "an earlier target journal"),
    (r"the FAIR 2026 overlap", "the overlap with earlier work"),
    (r"\bFAIR 2026\b", "the earlier conference paper"),
    (r"\bp7-carla312\b", "the CARLA environment"),
    (r"crossdataset_p4", "crossdataset_t"),
    (r"run_p7_", "run_s_"), (r"p4pipeline", "t_pipeline"),
    (rf"{T}P7_", "S_"), (rf"{T}P4_", "T_"), (rf"{T}p7_", "s_"), (rf"{T}p4_", "t_"),
    (r"\b(the|its|their) P4 permitted(\s+)(range|direction)", r"\1 permitted\2\3 of the taxonomy study"),
    (rf"{T}P4 permitted(\s+)(range|direction)", r"permitted\1\2 of the taxonomy study"),
    (rf"{T}P7{E}", "the dependency-graph study"), (rf"{T}P4{E}", "the taxonomy study"),
    (r"_hiss_", "_draft_"),
    (rf"{T}p7{E}", "s_pipe"), (rf"{T}p4{E}", "t_pipe"),
    (r"\buit\b|\bUIT\b", "<institution>"),
    (r"diabetesxai|evisyn|thieuanhvan", "<project>"),
    (r"QĐ-BYT", "QD-BYT"),
    (r"\b([Aa]) an internal", r"an internal"),
    (r"the authors's", "the authors'"),
    (r"\b([Tt]he) the (?=taxonomy study|dependency-graph study|CARLA environment)", r"\1 "),
    (r"\b(?:its|their|this) the (?=taxonomy study|dependency-graph study)", "the "),
]

# Applied to reviewer copies and code only (not to kg/, which keeps MoH quotations in Vietnamese).
SUBS_TEXT = [
    # quoted approvals in Vietnamese, with their surrounding comma or parentheses
    (rf'\s*\(\s*"[^"\n]*[{VI}][^"\n]*"\s*\)', ""),
    (rf',\s*"[^"\n]*[{VI}][^"\n]*"', ""),
    (rf':\s*"[^"\n]*[{VI}][^"\n]*"', ""),
    (rf'"[^"\n]*[{VI}][^"\n]*"', ""),
    # review records: paths and file names
    (r"\bin `(?:reviews|prereg)/(?:blind_review|fixcheck)[^`]*`", "internally"),
    (r"\s*\(`(?:reviews|prereg)/(?:blind_review|fixcheck)[^`]*`[^)]*\)", ""),
    (r"`(?:reviews|prereg)/(?:blind_review|fixcheck)[^`]*`", "an internal review record"),
    (r"`(?:blind_review|fixcheck)[^`]*`", "an internal review record"),
    (r"\b(?:blind_review|fixcheck)_[\w.-]+", "an internal review record"),
    # reviews of manuscript drafts and plans
    (r"(?:the |an )?(?:[Bb]lind|[Ii]nternal pre-submission) review of (?:the )?ESWA v\d manuscript", "an internal pre-submission review"),
    (r"(?:the |an )?[Bb]lind review of (?:the )?v\d draft", "an internal pre-submission review"),
    (r"(?:Section [\d.]+ of )?the v\d manuscript", "an earlier draft"),
    (r"ESWA v\d revision round", "revision round before submission"),
    (r"for the ESWA revision round", "for the revision round before submission"),
    (r"ESWA v\d", "a draft"),
    (r"\bESWA\b", "the target journal"),
    (r"[Bb]lind reviews\b", "internal reviews"),
    (r"\b[Bb]lind review\b", "internal review"),
    (r"\b[Bb]lind check\b", "internal check"),
    (r"reviewed blind\b", "reviewed internally"),
    (r"checked blind\b", "checked internally"),
    (r"[Bb]lind-review", "internal-review"),
    (r",?\s*relayed by the coordinator", ""),
    (r"\bthe coordinator\b", "the authors"),
    (r"\bcoordinator\b", "authors"),
    # notebook service
    (r"/kaggle/working", "<notebook working directory>"),
    (r"\bKaggle notebook", "hosted notebook"),
    (r"\bKaggle\b", "a hosted notebook service"),
]

FILEMAP = [(re.escape(src), dst) for src, dst in PREREG.items()]
FILEMAP += [(r"MANIFEST_sha256\.txt", "the authors' hash manifest")]

FORBID = re.compile(r"(?i:Thieu|Thiều|anh v[âa]n|Phuc|Phúc|thieuanhvan|evisyn|diabetesxai|\buit\b|student|MedicineKG|coordinator|"
                    r"blind[ _-]review|a an |authors's|fixcheck|reviews/|ESWA|HISS|taxonomy study permitted|S-the taxonomy|the the |"
                    r"(?<![\w-])p7(?![\w-])|(?<![\w-])p4(?![\w-]))|(?<![A-Za-z])[A-Z]:/")

CODE_DIRS = V4.CODE_DIRS + ["q1_posthoc_v5"]
CODE_EXT = V4.CODE_EXT
SKIP_CODE = {"ps_reviewer_copies.py"}

README_EXTRA = """
v5 additions
- reviewer_copies/ also holds the fifth post-hoc plan (diagnosis flags not counted as actions, the levers-only
  forced-lever baseline, the matched NHANES diabetes analysis); code/q1_posthoc_v5/ holds its code.
- Reviewer copies refer to internal reviews of the plans and drafts only as "internal review"; the review records
  themselves are not part of the bundle.
- The derived-output file crossdataset_t/cross_dataset_bootstrap.csv (an early NHANES HbA1c run with 67 patients, from
  before the final runs) is superseded by cross_dataset_bootstrap_v3.csv and is not used by any table; it is not part of
  this bundle and will be labelled superseded in the deposit.
- The SHA-256 hashes in the reviewer-copy headers are those of the unredacted originals; the originals and the hash
  manifest are held by the authors and will be deposited with the artefact DOI.
"""


CLEAN = [(r"\b([Aa]) an internal", "an internal"), (r"[Tt]he authors's", "the authors'"),
         (r"\b([Tt]he) the (?=authors)", r"\1 ")]


def redact(text, kind):
    n = 0
    subs = SUBS_ALL + (SUBS_TEXT + FILEMAP if kind != "kg" else []) + CLEAN
    for pat, rep in subs:
        text, k = re.subn(pat, rep, text)
        n += k
    return text, n


def put(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    total = 0
    for src, rel in V4.KG_FILES.items():
        t, n = redact(src.read_text(encoding="utf-8"), "kg")
        put(rel, t)
        total += n
    put("sparql/audit_unsupported_k1.rq", V4.RQ_K1)
    put("sparql/audit_unsupported_k2.rq", V4.RQ_K2)
    for d in CODE_DIRS:
        for f in sorted((TOOLS / d).rglob("*")):
            if f.is_dir() or "__pycache__" in f.parts or f.suffix not in CODE_EXT | {""} or f.name.startswith("."):
                continue
            if (f.suffix == "" and f.name != "LICENSE") or f.name in SKIP_CODE:
                continue
            t, n = redact(f.read_text(encoding="utf-8", errors="strict"), "code")
            put(redact((Path("code") / d / f.relative_to(TOOLS / d)).as_posix(), "code")[0], t)
            total += n
    for f in sorted((REPO / "src" / "depgraph").glob("*.py")):
        t, n = redact(f.read_text(encoding="utf-8"), "code")
        put(Path("code/depgraph") / f.name, t)
        total += n
    pre = P7 / "prereg"
    for src, dst in PREREG.items():
        raw = (pre / src).read_bytes()
        t, n = redact(raw.decode("utf-8"), "text")
        head = (f"*Reviewer copy for anonymised review. Original SHA-256 {hashlib.sha256(raw).hexdigest()}; {n} "
                f"substitutions (author and personal references, internal project codes, local paths, review records, "
                f"non-English approval quotes). The unredacted original will be deposited with the artefact DOI.*\n\n")
        put(Path("reviewer_copies") / dst, head + t)
        total += n
    put("README.md", V4.README.format(ns=NS_NEW).replace("the four post-hoc plans", "the five post-hoc plans")
        .replace("S-P1 to S-P4", "S-P1 to S-P5") + README_EXTRA)
    hits = []
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            t = f.read_text(encoding="utf-8")
            for m in FORBID.finditer(t):
                ctx = t[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                hits.append(f"{f.relative_to(OUT)}: {m.group(0)!r} in ...{ctx}...")
            if VIET.search(t) and f.relative_to(OUT).parts[0] != "kg":
                m = VIET.search(t)
                hits.append(f"{f.relative_to(OUT)}: Vietnamese letters ...{t[max(0, m.start() - 40):m.end() + 40]}...")
    if hits:
        print("\n".join(hits[:120]))
        sys.exit(f"anonymity scan: {len(hits)} hit(s); bundle not complete")
    sums = []
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"bundle: {len(sums)} files, {total} substitutions, anonymity scan clean")


if __name__ == "__main__":
    main()
