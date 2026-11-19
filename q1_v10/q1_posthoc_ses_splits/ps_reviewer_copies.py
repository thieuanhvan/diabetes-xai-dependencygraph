"""Anonymised reviewer copies of the preregistration, the post-hoc plans and the deviation log.

The originals are never edited (their SHA-256 values stay valid); each copy replaces author names, personal
references, internal project codes, local paths and non-English approval quotes by neutral text, by a fixed
substitution list, and records the original's SHA-256 and the number of substitutions in a header.
Usage: python -I ps_reviewer_copies.py
"""
import hashlib
import re
from pathlib import Path

PRE = Path("D:/20-study/uit/research/diabetesxai/paper7/prereg")
OUT = PRE / "reviewer_copies"
FILES = {"prereg_q1_extension_en_v3_20261111_1645.md": "preregistration_reviewer_copy.md",
         "posthoc_b_mlp_plan_en_v1_20261112_0520.md": "posthoc_plan_network_seeds_reviewer_copy.md",
         "posthoc_ses_freeze_plan_en_v1_20261112_0726.md": "posthoc_plan_ses_splits_ar_reviewer_copy.md",
         "deviations_log_q1_en.md": "deviation_log_reviewer_copy.md"}

# log rows for work outside the submitted article (a further disease domain prepared for a later version)
OMIT = re.compile(r"^\|[^|]*HTN[^|]*\|")

SUBS = [
    (r'\s*\("Có, hậu kiểm"\)', ""),
    (r': "Có, hậu kiểm"', ""),
    (r"[A-Z]:/[^\s`|),;]*", "<local path>"),
    (r"https?://github\.com/[^\s`|)]*", "<repository URL withheld for review>"),
    (r"for Van Thieu", "for the authors"),
    (r"Van Thieu|Thieu Anh Van|Phuc Do", "the authors"),
    (r"the student's own judgement", "the authors' own judgement"),
    (r"that decision is the student's", "that decision is the authors'"),
    (r"by a student at a public university", "by researchers at a public university"),
    (r"manual annotation by the student", "manual annotation by the authors"),
    (r"student decision", "author decision"),
    (r"[Aa]pproved by the student", "Approved by the authors"),
    (r"approved by the student", "approved by the authors"),
    (r"\bthe student\b", "the authors"),
    (r"P7 HISS manuscript v6", "the earlier manuscript draft"),
    (r"\bHISS\b", "an earlier target journal"),
    (r"the FAIR 2026 overlap", "the overlap with earlier work"),
    (r"\bFAIR 2026\b", "the earlier conference paper"),
    (r"\bp7-carla312\b", "the CARLA environment"),
    (r"\bP7\b", "the dependency-graph study"),
    (r"\bP4\b", "the taxonomy study"),
    (r"\bp7_", "s_"),
    (r"\bp4_", "t_"),
    (r"\buit\b|\bUIT\b", "<institution>"),
    (r"diabetesxai|evisyn|thieuanhvan", "<project>"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for src, dst in FILES.items():
        raw = (PRE / src).read_bytes()
        text = raw.decode("utf-8")
        lines = text.split("\n")
        kept = [ln for ln in lines if not OMIT.match(ln)]
        omitted = len(lines) - len(kept)
        text = "\n".join(kept)
        n = 0
        for pat, rep in SUBS:
            text, k = re.subn(pat, rep, text)
            n += k
        left = sorted(set(re.findall(r"[À-ỹ]", text)) - set("éèêëàâäôöûüçïîÉÀÖÜ×ÄöΔ"))
        extra = f"; {omitted} log row(s) on work not reported in this article omitted" if omitted else ""
        head = (f"*Reviewer copy for anonymised review. Original SHA-256 {hashlib.sha256(raw).hexdigest()}; "
                f"{n} substitutions (author and personal references, internal project codes, local paths, "
                f"non-English approval quotes){extra}. The unredacted original will be released after review.*\n\n")
        (OUT / dst).write_text(head + text, encoding="utf-8")
        print(f"{dst}: {n} substitutions; non-ASCII Latin letters left: {''.join(left) or 'none'}")


if __name__ == "__main__":
    main()
