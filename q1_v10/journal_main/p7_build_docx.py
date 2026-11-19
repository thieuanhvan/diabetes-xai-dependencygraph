"""Build the P7 English manuscript, supplementary and cover letter .docx with the shared pandoc template.

Same as _shared/tools/build_docx.py --no-toc, but with document language en-GB and bare URLs
turned into hyperlinks (every DOI/URL must be clickable). Optional PDF via Word COM is done separately.
Usage: python p7_build_docx.py <file.md> [...]
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, "D:/evisyn/projects/_shared/tools")
import build_docx as B  # noqa: E402

B.NO_TOC = True
URL = re.compile(r"(?<![<(\[])(https?://[^\s<>)\]]+[^\s<>)\].,;])")


def build(md_path):
    md_path = os.path.abspath(md_path)
    folder = os.path.dirname(md_path)
    out = os.path.splitext(md_path)[0] + ".docx"
    tmp = os.path.splitext(md_path)[0] + ".build.tmp.md"
    text = open(md_path, encoding="utf-8").read()
    text = URL.sub(r"<\1>", text)
    open(tmp, "w", encoding="utf-8").write(text)
    try:
        subprocess.run(["pandoc", tmp, "-f", "markdown", "-t", "docx", "-o", out, "--reference-doc", B.REFERENCE,
                        "-M", "lang=en-GB", "--resource-path", folder], check=True, cwd=folder)
    finally:
        os.remove(tmp)
    n = B.postprocess(out)
    a4, footer, tables, images = B.check(out)
    import zipfile
    links = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8").count("<w:hyperlink")
    print(f"{os.path.basename(out)}: A4={a4} captions={n} tables={tables} images={images} hyperlinks={links}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(p)
