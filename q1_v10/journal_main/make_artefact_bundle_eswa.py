"""Anonymised artefact bundle for the ESWA review (v4): knowledge graphs (Turtle), SPARQL queries, code and the
reviewer copies of the preregistration, post-hoc plans and deviation log. No survey data, no fitted models, no
guideline text beyond the short quotations of at most twelve words that the extraction protocol records.

Redaction: the fixed substitution list of ps_reviewer_copies.py (author and personal references, internal project
codes, local paths, repository URL, non-English approval quotes), extended for the S-P4 approval quote and the
knowledge-graph namespace. The hypertension addendum, its code and its log rows are
included (v4 reports hypertension as a third domain). Every text file is scanned after redaction for author names, project codes, paths and
Vietnamese letters; a hit stops the script.

Usage: python -I make_artefact_bundle_eswa.py
Output: paper7/submission/2-eswa/artefacts/ (folders kg, sparql, code, reviewer_copies; README.md; SHA256SUMS.txt)
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

TOOLS = Path("D:/evisyn/projects/diabetesxai/paper7/tools")
sys.path.insert(0, str(TOOLS / "q1_posthoc_ses_splits"))
import ps_reviewer_copies as RC  # noqa: E402

P7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
OUT = P7 / "submission" / "2-eswa" / "artefacts"
REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
NS_OLD = "https://github.com/thieuanhvan/diabetes-xai-dependencygraph/kg#"
NS_NEW = "https://example.org/anonymised-review/kg#"

SUBS = [(r'\s*\("Có, sửa v4"\)', ""), (r', "Có, sửa v4"', ""), (r'"Có, sửa v4"', "")]
SUBS += [(re.escape(NS_OLD), NS_NEW)] + RC.SUBS + [(r"\bp7\b", "s_pipe"), (r"\bp4\b", "t_pipe"),
                                                  (r"\bP7_", "S_"), (r"\bP4_", "T_"), ("QĐ-BYT", "QD-BYT"),
         ("crossdataset_p4", "crossdataset_t"),
         ("run_p7_", "run_s_"), ("p4pipeline", "t_pipeline"),
         ("student_hard_cap_usd", "hard_cap_usd"), (r"[Aa]nh Vân", "the authors"), (r"\bThe student\b", "The authors"),
         (r"\bthe student\b", "the authors"), (r"\bstudent\b", "author")]
SKIP_CODE = {"ps_reviewer_copies.py"}  # holds the redaction list itself
PREREG = dict(RC.FILES)
PREREG["posthoc_forced_lever_plan_en_v1_20261112_0957.md"] = "posthoc_plan_forced_lever_reviewer_copy.md"
PREREG["prereg_addendum_htn_en_v3_20261112_0840.md"] = "preregistration_addendum_hypertension_reviewer_copy.md"
OMIT = re.compile(r"(?!x)x")  # v4: hypertension is reported in the article, so no log row is omitted

CODE_DIRS = ["crossdataset_p4", "kg_export", "q1_domain_ckd", "q1_ext_b", "q1_posthoc_ses_splits",
             "q1_posthoc_forced_lever", "nhis_replication", "q1_domain_htn"]
CODE_EXT = {".py", ".json", ".txt", ".sh", ".md"}
FORBID = re.compile(r"(?i:Thieu|Thiều|Phuc|Phúc|thieuanhvan|evisyn|diabetesxai|\buit\b|student|MedicineKG|"
                    r"(?<!-)\bp7\b|(?<!-)\bp4\b)|(?<![A-Za-z])[A-Z]:/")
VIET = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)

KG_FILES = {
    P7 / "outputs/kg_export/dependency_graph.ttl": "kg/diabetes_dependency_graph.ttl",
    P7 / "outputs/kg_export/dependency_graph_nodes.csv": "kg/diabetes_nodes_roles_codes.csv",
    P7 / "outputs/kg_export/dependency_graph_triples.csv": "kg/diabetes_triples_provenance.csv",
    P7 / "outputs/q1_domain_ckd/a2_analysis/ckd_domain_graph.ttl": "kg/ckd_domain_graph.ttl",
    P7 / "outputs/q1_domain_ckd/a0_role_table/ckd_role_table.csv": "kg/ckd_role_table.csv",
    P7 / "outputs/q1_domain_ckd/a0_role_table/ckd_lock_set.txt": "kg/ckd_lock_set.txt",
    P7 / "outputs/q1_domain_ckd/a1_extraction/agreement/agreement_kdigo.json": "kg/kdigo_agreement.json",
    P7 / "outputs/q1_domain_ckd/a1_extraction/agreement/kdigo_passages_extractor1_claude_v1.csv": "kg/kdigo_passages_extractor1.csv",
    P7 / "outputs/q1_domain_ckd/a1_extraction/agreement/kdigo_passages_extractor2_claude_fallback_v2.csv": "kg/kdigo_passages_extractor2.csv",
    P7 / "outputs/q1_domain_ckd/a2_analysis/sparql_unit_test.json": "sparql/check_python_vs_sparql_random_sets.json",
    P7 / "outputs/q1_domain_ckd/a2_analysis/sparql_audit_main.json": "sparql/check_python_vs_sparql_ckd_main.json",
}

RQ_K1 = """# Unsupported-indicator audit, primary reading (k = 1, lever sources), as evaluated by code/q1_domain_ckd/a2_sparql_check.py.
# The change set S of a counterfactual is asserted as temporary triples  kg:<feature> kg:inS true .  before the query,
# and VALUES lists the features of S. ASK returns true when S contains an indicator with no lever in S that has a
# Statement (route) into it from an admitted authority (here KDIGO; use kg:ADA for the diabetes domain).
PREFIX kg: <https://example.org/anonymised-review/kg#>
ASK {
  VALUES ?v { kg:BMI kg:GenHlth }                       # the change set S
  ?rav kg:ofVariable ?v ; kg:assignedIn kg:CKD ; kg:role kg:indicator .
  FILTER NOT EXISTS {
    ?u kg:inS true .
    ?rau kg:ofVariable ?u ; kg:assignedIn kg:CKD ; kg:role kg:lever .
    [] a kg:Statement ; kg:subject ?u ; kg:object ?v ; kg:authority ?au .
    VALUES ?au { kg:KDIGO }
  }
}
"""
RQ_K2 = """# Secondary reading: path of at most two Statements through a treatable node (permissive: the treatable node need not
# be in S; strict: add  ?t kg:inS true .). Same conventions as audit_unsupported_k1.rq.
PREFIX kg: <https://example.org/anonymised-review/kg#>
ASK {
  VALUES ?v { kg:BMI kg:GenHlth }
  ?rav kg:ofVariable ?v ; kg:assignedIn kg:CKD ; kg:role kg:indicator .
  FILTER NOT EXISTS {
    { ?u kg:inS true . ?rau kg:ofVariable ?u ; kg:assignedIn kg:CKD ; kg:role kg:lever .
      [] a kg:Statement ; kg:subject ?u ; kg:object ?v ; kg:authority ?a1 . VALUES ?a1 { kg:KDIGO kg:ADA } }
    UNION
    { ?u kg:inS true . ?rau kg:ofVariable ?u ; kg:assignedIn kg:CKD ; kg:role kg:lever .
      ?rat kg:ofVariable ?t ; kg:assignedIn kg:CKD ; kg:role kg:treatable .
      [] a kg:Statement ; kg:subject ?u ; kg:object ?t ; kg:authority ?a2 . VALUES ?a2 { kg:KDIGO kg:ADA }
      [] a kg:Statement ; kg:subject ?t ; kg:object ?v ; kg:authority ?a3 . VALUES ?a3 { kg:KDIGO kg:ADA } }
  }
}
"""

README = """# Artefact bundle for review

Available to reviewers of the submitted article. Anonymised: author names, project codes, local paths, the repository
URL and the knowledge-graph namespace were replaced by neutral text (namespace: {ns}). The public version will be
deposited after review with the original namespace.

Contents
- kg/: the diabetes dependency graph in RDF Turtle (nodes with roles and terminology codes, routes as reified statements
  with authority, location, strength and population), its node and triple tables, the CKD domain graph used by the SPARQL
  audit, the CKD role table and lock set derived by script, and the KDIGO extraction outputs of both extractors with the
  quotation (at most twelve words) and page of every passage and the agreement statistics. ADA edges carry the
  recommendation number or page and a paraphrase only, because the ADA terms of use restrict reproducing its text.
  Ministry of Health edges carry their quotation in the original Vietnamese (language tag vi).
  No hypertension graph is included: the agreed graph was not reached, and the AHA/ACC licence forbids redistributing
  its text.
- sparql/: the audit queries (k = 1 and two-edge readings) and the recorded Python-versus-SPARQL checks.
- code/: the analysis code (data harmonisation calls, role derivation, runs, analyses, post-hoc analyses S-P1 to S-P4,
  graph export) and the audit implementation (code/depgraph). Third-party CARLA code is vendored with its licence.
- reviewer_copies/: the preregistration, the hypertension addendum, the four post-hoc plans and the deviation log, redacted as above; each starts
  with the SHA-256 of its unredacted original.

Not included: survey data (public, from the US CDC; the code rebuilds the tables from the public files), fitted models,
counterfactual tables, and guideline documents. The code expects the public survey files and the earlier taxonomy
pipeline it imports; paths were replaced by <local path>, so the code documents the analysis and is not runnable
without that setup.

SHA256SUMS.txt lists every file of this bundle.
"""


def redact(text):
    n = 0
    for pat, rep in SUBS:
        text, k = re.subn(pat, rep, text)
        n += k
    return text, n


def put(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    total = 0
    for src, rel in KG_FILES.items():
        t, n = redact(src.read_text(encoding="utf-8"))
        put(rel, t)
        total += n
    put("sparql/audit_unsupported_k1.rq", RQ_K1)
    put("sparql/audit_unsupported_k2.rq", RQ_K2)
    for d in CODE_DIRS:
        for f in sorted((TOOLS / d).rglob("*")):
            if f.is_dir() or "__pycache__" in f.parts or f.suffix not in CODE_EXT | {""} or f.name.startswith("."):
                continue
            if (f.suffix == "" and f.name != "LICENSE") or f.name in SKIP_CODE:
                continue
            t, n = redact(f.read_text(encoding="utf-8", errors="strict"))
            put(redact((Path("code") / d / f.relative_to(TOOLS / d)).as_posix())[0], t)
            total += n
    for f in sorted((REPO / "src" / "depgraph").glob("*.py")):
        t, n = redact(f.read_text(encoding="utf-8"))
        put(Path("code/depgraph") / f.name, t)
        total += n
    pre = P7 / "prereg"
    for src, dst in PREREG.items():
        raw = (pre / src).read_bytes()
        lines = raw.decode("utf-8").split("\n")
        kept = [ln for ln in lines if not OMIT.match(ln)]
        t, n = redact("\n".join(kept))
        head = (f"*Reviewer copy for anonymised review. Original SHA-256 {hashlib.sha256(raw).hexdigest()}; {n} "
                f"substitutions (author and personal references, internal project codes, local paths, non-English "
                f"approval quotes); {len(lines) - len(kept)} log row(s) on work not reported in this article omitted. "
                f"The unredacted original will be released after review.*\n\n")
        put(Path("reviewer_copies") / dst, head + t)
        total += n
    put("README.md", README.format(ns=NS_NEW))
    hits = []
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            t = f.read_text(encoding="utf-8")
            for m in FORBID.finditer(t):
                ctx = t[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                hits.append(f"{f.relative_to(OUT)}: {m.group(0)!r} in ...{ctx}...")
            if VIET.search(t) and f.relative_to(OUT).parts[0] != "kg":  # kg/: MoH quotations in the original Vietnamese
                hits.append(f"{f.relative_to(OUT)}: Vietnamese letters")
    if hits:
        print("\n".join(hits[:80]))
        sys.exit(f"anonymity scan: {len(hits)} hit(s); bundle not complete")
    sums = []
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"bundle: {len(sums)} files, {total} substitutions, anonymity scan clean")


if __name__ == "__main__":
    main()
