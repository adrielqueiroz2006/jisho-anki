#!/usr/bin/env python3
"""Gera as fontes embutidas em addon/fonts/ (woff2 reduzidas).

- Shippori Mincho (OFL): Regular e Bold, só com kana, pontuação e os kanji do JIS X 0208
  (os mesmos ~6,3 mil do KANJIDIC2 com código jis208). O que ficar de fora cai na fonte do sistema.
- Literata (OFL): romana e itálico, só latim, para o texto em português/inglês.

Requer: pip install fonttools brotli. Roda uma vez; o resultado vai junto no addon.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "addon", "fonts")
CACHE = os.path.join(ROOT, "data", "raw", "fonts")
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"

# (url, arquivo no addon; o prefixo _ protege contra a verificação de mídia do Anki)
JOBS = [
    (f"{GF}/shipporimincho/ShipporiMincho-Regular.ttf", "_shipporimincho-regular.woff2", "jp"),
    (f"{GF}/shipporimincho/ShipporiMincho-Bold.ttf", "_shipporimincho-bold.woff2", "jp"),
    (f"{GF}/literata/Literata%5Bopsz,wght%5D.ttf", "_literata.woff2", "latin"),
    (f"{GF}/literata/Literata-Italic%5Bopsz,wght%5D.ttf", "_literata-italic.woff2", "latin"),
]
LICENSES = {
    "OFL-ShipporiMincho.txt": f"{GF}/shipporimincho/OFL.txt",
    "OFL-Literata.txt": f"{GF}/literata/OFL.txt",
}


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print("baixando", url)
        req = urllib.request.Request(url, headers={"User-Agent": "jisho-card-build/1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    return path


def jp_codepoints():
    path = os.path.join(ROOT, "data", "raw", "jmdict", "kanjidic2-all.json.zip")
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read(z.namelist()[0]).decode("utf-8"))
    cps = set()
    for c in data["characters"]:
        if any(cp["type"] == "jis208" for cp in c["codepoints"]):
            cps.add(ord(c["literal"]))
    cps.update(range(0x3000, 0x3100))   # pontuação CJK, hiragana, katakana
    cps.update(range(0xFF00, 0xFFF0))   # formas de largura total
    cps.update(range(0x20, 0x7F))
    cps.update([0x3005, 0x3006, 0x30FC, 0x2026, 0x2015, 0x25B6, 0x25B8, 0x3010, 0x3011])
    return cps


def latin_codepoints():
    cps = set(range(0x20, 0x7F)) | set(range(0xA0, 0x180))
    cps.update([0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2192, 0x2190, 0x00D7])
    return cps


def build(src, dst, cps):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    opts.name_IDs = ["*"]
    opts.drop_tables += ["DSIG"]
    font = subset.load_font(src, opts)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=sorted(cps))
    sub.subset(font)
    subset.save_font(font, dst, opts)


def main():
    os.makedirs(OUT, exist_ok=True)
    jp, latin = jp_codepoints(), latin_codepoints()
    for url, outname, kind in JOBS:
        src = fetch(url, os.path.basename(url).replace("%5B", "[").replace("%5D", "]"))
        dst = os.path.join(OUT, outname)
        build(src, dst, jp if kind == "jp" else latin)
        print(f"{outname}: {os.path.getsize(dst) / 1024:.0f} KB")
    for name, url in LICENSES.items():
        path = fetch(url, name)
        with open(path, "rb") as f, open(os.path.join(OUT, name), "wb") as g:
            g.write(f.read())


if __name__ == "__main__":
    sys.exit(main())
