#!/usr/bin/env python3
"""Critério da Fase 1: consultar 食べる, 日本, 水, きれい e 生 em menos de 50 ms cada."""
import os
import sys
import time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
from addon import lookup  # noqa: E402

WORDS = ["食べる", "日本", "水", "きれい", "生"]
LIMIT_MS = 50


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "build", "dicionario.sqlite")
    conn = lookup.open_db(path)
    ok = True
    for w in WORDS:
        t = time.perf_counter()
        entries = lookup.find_entries(conn, w)
        kanji = [lookup.get_kanji(conn, c) for c in w if lookup.get_kanji(conn, c)]
        ms = (time.perf_counter() - t) * 1000
        flag = "ok" if ms < LIMIT_MS else "LENTO"
        ok = ok and ms < LIMIT_MS
        print(f"{w}: {len(entries)} entradas, {len(kanji)} kanji, {ms:.1f} ms [{flag}]")
        for e in entries[:3]:
            forms = "・".join(k["t"] for k in e["kanji"][:2]) or "-"
            kana = "・".join(r["t"] for r in e["kana"][:2])
            gloss = "; ".join(e["senses"][0]["gloss"][:3])
            pos = ",".join(e["senses"][0]["pos"])
            print(f"    {forms} 【{kana}】 ({pos}) {gloss}  exemplos={len(e['examples'])}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
