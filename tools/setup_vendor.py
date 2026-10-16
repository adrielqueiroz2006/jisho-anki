#!/usr/bin/env python3
"""Instala em addon/vendor/ as bibliotecas de terceiros em Python puro que o addon embute.

  python tools/setup_vendor.py

- Janome 0.5.0 (furigana das frases) e gTTS 2.5.4 (voz de reserva) vêm do PyPI. O Janome tem ~137 MB de
  dicionário em Python, por isso não é versionado no Git.
- addon/vendor/edge_tts (cópia mínima do edge-tts, LGPL) é versionado, porque tem uma alteração nossa.

Rode uma vez depois de clonar o repositório, antes de `tools/package.py` ou dos testes.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "addon", "vendor")
PACKAGES = ["janome==0.5.0", "gTTS==2.5.4"]


def main():
    os.makedirs(VENDOR, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *PACKAGES, "--target", VENDOR, "--no-deps", "--no-compile",
         "--upgrade", "--quiet"],
        check=True,
    )
    shutil.rmtree(os.path.join(VENDOR, "bin"), ignore_errors=True)  # scripts de linha de comando que não usamos
    for name in ("janome", "gtts", "edge_tts"):
        if not os.path.isdir(os.path.join(VENDOR, name)):
            sys.exit(f"faltou addon/vendor/{name}")
    print("ok: addon/vendor pronto")


if __name__ == "__main__":
    main()
