#!/usr/bin/env python3
"""Modo desenvolvimento no Windows: liga a pasta addon/ à pasta de addons do Anki por uma junção.

Assim cada edição em addon/ vale ao reabrir o Anki, sem reempacotar. Feche o Anki antes.
  python tools/install_dev.py            # cria a junção
  python tools/install_dev.py --remove   # desfaz (não apaga a pasta addon/)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "addon")
DEST = os.path.join(os.environ["APPDATA"], "Anki2", "addons21", "jisho_card")


def main():
    if "--remove" in sys.argv:
        if os.path.isdir(DEST):
            os.rmdir(DEST)  # numa junção, só remove o link
            print("removido:", DEST)
        return
    if os.path.exists(DEST):
        sys.exit(f"já existe: {DEST}")
    subprocess.run(["cmd", "/c", "mklink", "/J", DEST, SRC], check=True)
    print("ok: reabra o Anki")


if __name__ == "__main__":
    main()
