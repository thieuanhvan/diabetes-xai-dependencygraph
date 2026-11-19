"""Clear author metadata in the ESWA docx files and assemble the anonymised submission folder.

Usage: python -I make_submission_eswa.py <stamp> [version]   (e.g. 20261112_0937 v3; version defaults to v4)
- Clears dc:creator, cp:lastModifiedBy, dc:title (core.xml) and Company (app.xml) in every versioned docx in place.
- Writes paper7/submission/2-eswa/ with neutral names: manuscript.docx/.pdf, supplementary.docx/.pdf,
  highlights.docx, titlepage.docx, coverletter.docx, figures (PDF/EPS, 1000 dpi PNG) and the reviewer copies
  of the preregistration, the post-hoc plans and the deviation log (v4: taken from the anonymised artefact bundle
  built by make_artefact_bundle_eswa.py, so that they include the latest log rows; stale copies are removed).
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

P7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
SUB = P7 / "submission" / "2-eswa"
FIG = P7 / "outputs" / "journal_main" / "figures_v3"
REV = P7 / "submission" / "2-eswa" / "artefacts" / "reviewer_copies"
PARTS = ["manuscript", "supplementary", "highlights", "titlepage", "coverletter"]


def clear_meta(path):
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                t = data.decode("utf-8")
                for tag in ("dc:creator", "cp:lastModifiedBy", "dc:title"):
                    t = re.sub(rf"<{tag}>[^<]*</{tag}>", f"<{tag}></{tag}>", t)
                data = t.encode("utf-8")
            elif item.filename == "docProps/app.xml":
                data = re.sub(r"<Company>[^<]*</Company>", "<Company></Company>", data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)


def main(stamp, ver="v4"):
    SUB.mkdir(parents=True, exist_ok=True)
    (SUB / "figures").mkdir(exist_ok=True)
    (SUB / "reviewer_copies").mkdir(exist_ok=True)
    for part in PARTS:
        src = P7 / f"thieuanhvan_diabetesxai_paper7_{part}_eswa_en_{ver}_{stamp}.docx"
        if not src.exists():
            # parts not re-exported in this version keep their latest file in the working folder
            src = sorted(P7.glob(f"thieuanhvan_diabetesxai_paper7_{part}_eswa_en_v*_*.docx"))[-1]
        print("source:", src.name)
        clear_meta(src)
        shutil.copy2(src, SUB / f"{part}.docx")
        if part in ("manuscript", "supplementary"):
            shutil.copy2(src.with_suffix(".pdf"), SUB / f"{part}.pdf")
    for f in sorted(FIG.glob("fig*")):
        if f.suffix in (".pdf", ".eps", ".png"):
            shutil.copy2(f, SUB / "figures" / f.name)
    for f in (SUB / "reviewer_copies").glob("*.md"):
        f.unlink()
    for f in sorted(REV.glob("*.md")):
        shutil.copy2(f, SUB / "reviewer_copies" / f.name)
    for f in sorted(SUB.rglob("*")):
        if f.is_file():
            print(f.relative_to(SUB), f.stat().st_size)


if __name__ == "__main__":
    main(*sys.argv[1:3])
