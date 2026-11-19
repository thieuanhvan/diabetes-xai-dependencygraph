"""Replace the Vietnamese page label 'Trang' with 'Page' in the footers of English .docx files.
Usage: python -I p7_footer_en.py <file.docx> [...]
"""
import os
import shutil
import sys
import zipfile

for path in sys.argv[1:]:
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        n = 0
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/footer") and item.filename.endswith(".xml"):
                text = data.decode("utf-8")
                n += text.count(">Trang <")
                data = text.replace(">Trang <", ">Page <").encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print(f"{os.path.basename(path)}: {n} footer label(s) set to Page")
