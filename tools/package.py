#!/usr/bin/env python3
"""Empacota addon/ em build/jisho_card.ankiaddon (zip com os arquivos na raiz, como o Anki exige)."""
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "addon")
OUT = os.path.join(ROOT, "build", "jisho_card.ankiaddon")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(SRC):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith((".pyc", ".pyo")):
                    continue
                path = os.path.join(folder, name)
                z.write(path, os.path.relpath(path, SRC).replace(os.sep, "/"))
    print(f"ok: {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
