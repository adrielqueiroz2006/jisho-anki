#!/usr/bin/env python3
"""Gera o dicionario.sqlite do addon Jisho Card.

Fontes (todas abertas, ver addon/LICENSES.md):
  - JMdict com exemplos (jmdict-simplified, EDRDG, CC BY-SA 4.0)
  - KANJIDIC2 (jmdict-simplified, EDRDG, CC BY-SA 4.0)
  - KanjiVG (CC BY-SA 3.0)
  - Tatoeba jpn/por/eng (CC BY 2.0 FR)

Uso:
  python tools/build_db.py                  # baixa o que faltar e gera build/dicionario.sqlite
  python tools/build_db.py --release        # também gera .xz e .sha256 para o release do GitHub

Esquema (versão 1):
  meta(key, value)
  tag(code, description)                   # tags do JMdict (v1, vt, n, adj-na...)
  entry(id, common, data)                  # data = JSON compacto da entrada
  form(text, entry_id, kind, common, idx)  # índice de busca: kind 'k' (kanji) ou 'r' (kana)
  sentence(id, jpn, por, eng)              # frases do Tatoeba que têm tradução
  example(entry_id, sense_idx, sentence_id, word)
  kanji(literal, strokes, grade, jlpt_old, freq, radical_num, radical,
        on_yomi, kun_yomi, meanings_en, meanings_pt, strokes_svg)
"""
import argparse
import bz2
import datetime
import gzip
import hashlib
import json
import lzma
import os
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

SCHEMA_VERSION = 1

JMDICT_TAG = "3.6.2+20261012204142"
JMDICT_BASE = "https://github.com/scriptin/jmdict-simplified/releases/download/" + JMDICT_TAG.replace("+", "%2B")
KANJIVG_TAG = "r20260714"
KANJIVG_VERSION = "20260714"
TATOEBA_BASE = "https://downloads.tatoeba.org/exports/per_language"

# nome do arquivo local -> URL
SOURCES = {
    "jmdict/jmdict-examples-eng.json.zip": f"{JMDICT_BASE}/jmdict-examples-eng-{JMDICT_TAG.replace('+', '%2B')}.json.zip",
    "jmdict/kanjidic2-all.json.zip": f"{JMDICT_BASE}/kanjidic2-all-{JMDICT_TAG.replace('+', '%2B')}.json.zip",
    "kanjivg/kanjivg.xml.gz": f"https://github.com/KanjiVG/kanjivg/releases/download/{KANJIVG_TAG}/kanjivg-{KANJIVG_VERSION}.xml.gz",
    "tatoeba/jpn_sentences.tsv.bz2": f"{TATOEBA_BASE}/jpn/jpn_sentences.tsv.bz2",
    "tatoeba/jpn-por_links.tsv.bz2": f"{TATOEBA_BASE}/jpn/jpn-por_links.tsv.bz2",
    "tatoeba/jpn-eng_links.tsv.bz2": f"{TATOEBA_BASE}/jpn/jpn-eng_links.tsv.bz2",
    "tatoeba/por_sentences.tsv.bz2": f"{TATOEBA_BASE}/por/por_sentences.tsv.bz2",
    "tatoeba/eng_sentences.tsv.bz2": f"{TATOEBA_BASE}/eng/eng_sentences.tsv.bz2",
}

SCHEMA_SQL = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE tag (code TEXT PRIMARY KEY, description TEXT NOT NULL);
CREATE TABLE entry (id INTEGER PRIMARY KEY, common INTEGER NOT NULL, data TEXT NOT NULL);
CREATE TABLE form (
    text TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    common INTEGER NOT NULL,
    idx INTEGER NOT NULL
);
CREATE TABLE sentence (id INTEGER PRIMARY KEY, jpn TEXT NOT NULL, por TEXT, eng TEXT);
CREATE TABLE example (
    entry_id INTEGER NOT NULL,
    sense_idx INTEGER NOT NULL,
    sentence_id INTEGER NOT NULL,
    word TEXT NOT NULL
);
CREATE TABLE kanji (
    literal TEXT PRIMARY KEY,
    strokes INTEGER,
    grade INTEGER,
    jlpt_old INTEGER,
    freq INTEGER,
    radical_num INTEGER,
    radical TEXT,
    on_yomi TEXT NOT NULL,
    kun_yomi TEXT NOT NULL,
    meanings_en TEXT NOT NULL,
    meanings_pt TEXT NOT NULL,
    strokes_svg TEXT
);
"""

INDEX_SQL = """
CREATE INDEX idx_form_text ON form(text);
CREATE INDEX idx_form_entry ON form(entry_id);
CREATE INDEX idx_example_entry ON example(entry_id);
"""


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------- download

def download(raw_dir):
    for rel, url in SOURCES.items():
        path = os.path.join(raw_dir, *rel.split("/"))
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log(f"baixando {url}")
        tmp = path + ".part"
        req = urllib.request.Request(url, headers={"User-Agent": "jisho-card-build/1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp, path)


def raw(raw_dir, rel):
    path = os.path.join(raw_dir, *rel.split("/"))
    if not os.path.exists(path):
        sys.exit(f"arquivo ausente: {path} (rode sem --no-download)")
    return path


def read_json_zip(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".json")]
        return json.loads(z.read(names[0]).decode("utf-8"))


def iter_tsv_bz2(path):
    with bz2.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n").split("\t")


# --------------------------------------------------------------------------- JMdict

def build_jmdict(conn, raw_dir):
    log("lendo JMdict (com exemplos)...")
    data = read_json_zip(raw(raw_dir, "jmdict/jmdict-examples-eng.json.zip"))
    conn.executemany("INSERT INTO tag VALUES (?, ?)", sorted(data["tags"].items()))
    conn.execute("INSERT INTO meta VALUES ('jmdict_date', ?)", (data.get("dictDate", ""),))
    conn.execute("INSERT INTO meta VALUES ('jmdict_version', ?)", (data.get("version", ""),))

    example_sentences = {}  # id -> (jpn, eng), para frases que sumiram do Tatoeba
    entries = []
    forms = []
    examples = []
    for w in data["words"]:
        eid = int(w["id"])
        kanji = [{"t": k["text"], "c": int(k["common"]), "g": k["tags"]} for k in w["kanji"]]
        kana = [{"t": r["text"], "c": int(r["common"]), "g": r["tags"], "k": r["appliesToKanji"]}
                for r in w["kana"]]
        senses = []
        for si, s in enumerate(w["sense"]):
            glosses = [g["text"] for g in s["gloss"] if g["lang"] == "eng"]
            if not glosses:
                continue
            senses.append({
                "pos": s["partOfSpeech"],
                "gloss": glosses,
                "misc": s["misc"],
                "field": s["field"],
                "dial": s["dialect"],
                "info": s["info"],
                "ak": s["appliesToKanji"],
                "ar": s["appliesToKana"],
            })
            for ex in s.get("examples", []):
                if ex["source"]["type"] != "tatoeba":
                    continue
                sid = int(ex["source"]["value"])
                sents = {x["lang"]: x["text"] for x in ex["sentences"]}
                if "jpn" not in sents:
                    continue
                example_sentences[sid] = (sents["jpn"], sents.get("eng"))
                examples.append((eid, len(senses) - 1, sid, ex["text"]))
        if not senses:
            continue
        common = int(any(k["c"] for k in kanji) or any(r["c"] for r in kana))
        entries.append((eid, common, json.dumps(
            {"k": kanji, "r": kana, "s": senses}, ensure_ascii=False, separators=(",", ":"))))
        for i, k in enumerate(kanji):
            forms.append((k["t"], eid, "k", k["c"], i))
        for i, r in enumerate(kana):
            forms.append((r["t"], eid, "r", r["c"], i))
    conn.executemany("INSERT INTO entry VALUES (?, ?, ?)", entries)
    conn.executemany("INSERT INTO form VALUES (?, ?, ?, ?, ?)", forms)
    conn.executemany("INSERT INTO example VALUES (?, ?, ?, ?)", examples)
    log(f"  {len(entries)} entradas, {len(forms)} formas, {len(examples)} exemplos")
    return example_sentences


# --------------------------------------------------------------------------- Tatoeba

def build_sentences(conn, raw_dir, example_sentences):
    log("lendo Tatoeba...")
    links_por = {}
    for row in iter_tsv_bz2(raw(raw_dir, "tatoeba/jpn-por_links.tsv.bz2")):
        links_por.setdefault(int(row[0]), int(row[1]))
    links_eng = {}
    for row in iter_tsv_bz2(raw(raw_dir, "tatoeba/jpn-eng_links.tsv.bz2")):
        links_eng.setdefault(int(row[0]), int(row[1]))

    need_por = set(links_por.values())
    need_eng = set(links_eng.values())
    por_text = {}
    for row in iter_tsv_bz2(raw(raw_dir, "tatoeba/por_sentences.tsv.bz2")):
        i = int(row[0])
        if i in need_por:
            por_text[i] = row[2]
    eng_text = {}
    for row in iter_tsv_bz2(raw(raw_dir, "tatoeba/eng_sentences.tsv.bz2")):
        i = int(row[0])
        if i in need_eng:
            eng_text[i] = row[2]

    rows = {}
    for row in iter_tsv_bz2(raw(raw_dir, "tatoeba/jpn_sentences.tsv.bz2")):
        sid = int(row[0])
        por = por_text.get(links_por.get(sid))
        eng = eng_text.get(links_eng.get(sid))
        if sid in example_sentences and not eng:
            eng = example_sentences[sid][1]
        if por or eng or sid in example_sentences:
            rows[sid] = (sid, row[2], por, eng)
    # frases de exemplo do JMdict que não existem mais no export atual
    for sid, (jpn, eng) in example_sentences.items():
        rows.setdefault(sid, (sid, jpn, None, eng))
    conn.executemany("INSERT INTO sentence VALUES (?, ?, ?, ?)", rows.values())
    n_por = sum(1 for r in rows.values() if r[2])
    log(f"  {len(rows)} frases ({n_por} com tradução em português)")


# --------------------------------------------------------------------------- KANJIDIC2 + KanjiVG

def radical_char(num):
    """Radical Kangxi nº N (1..214) -> ideograma (U+2F00 normalizado)."""
    if not num or not 1 <= num <= 214:
        return None
    return unicodedata.normalize("NFKC", chr(0x2F00 + num - 1))


def load_kanjivg(path):
    """literal -> lista de 'd' dos traços, em ordem."""
    strokes = {}
    pat_kanji = re.compile(r"^kvg:kanji_([0-9a-f]{5})$")
    pat_stroke = re.compile(r"-s(\d+)$")
    with gzip.open(path, "rb") as f:
        for _event, el in ET.iterparse(f, events=("end",)):
            if not el.tag.endswith("kanji"):
                continue
            m = pat_kanji.match(el.get("id", ""))
            if m:
                paths = []
                for p in el.iter():
                    if p.tag.endswith("path") and p.get("d"):
                        sm = pat_stroke.search(p.get("id", ""))
                        if sm:
                            paths.append((int(sm.group(1)), p.get("d")))
                paths.sort()
                strokes[chr(int(m.group(1), 16))] = [d for _n, d in paths]
            el.clear()
    return strokes


def build_kanji(conn, raw_dir):
    log("lendo KANJIDIC2 e KanjiVG...")
    kd = read_json_zip(raw(raw_dir, "jmdict/kanjidic2-all.json.zip"))
    conn.execute("INSERT INTO meta VALUES ('kanjidic_date', ?)", (kd.get("version", ""),))
    svg = load_kanjivg(raw(raw_dir, "kanjivg/kanjivg.xml.gz"))
    rows = []
    for c in kd["characters"]:
        lit = c["literal"]
        misc = c["misc"]
        rad = next((r["value"] for r in c["radicals"] if r["type"] == "classical"), None)
        on, kun, en, pt = [], [], [], []
        for g in c["readingMeaning"]["groups"] if c.get("readingMeaning") else []:
            for r in g["readings"]:
                if r["type"] == "ja_on":
                    on.append(r["value"])
                elif r["type"] == "ja_kun":
                    kun.append(r["value"])
            for m in g["meanings"]:
                if m["lang"] == "en":
                    en.append(m["value"])
                elif m["lang"] == "pt":
                    pt.append(m["value"])
        rows.append((
            lit,
            (misc["strokeCounts"] or [None])[0],
            misc.get("grade"),
            misc.get("jlptLevel"),
            misc.get("frequency"),
            rad,
            radical_char(rad),
            json.dumps(on, ensure_ascii=False),
            json.dumps(kun, ensure_ascii=False),
            json.dumps(en, ensure_ascii=False),
            json.dumps(pt, ensure_ascii=False),
            json.dumps(svg[lit], separators=(",", ":")) if lit in svg else None,
        ))
    conn.executemany("INSERT INTO kanji VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    missing = sum(1 for r in rows if r[-1] is None)
    log(f"  {len(rows)} kanji ({len(svg)} no KanjiVG, {missing} sem traços)")


# --------------------------------------------------------------------------- main

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default=os.path.join(root, "data", "raw"))
    ap.add_argument("--out", default=os.path.join(root, "build", "dicionario.sqlite"))
    ap.add_argument("--no-download", action="store_true", help="não baixa nada; usa só o que já está em --raw-dir")
    ap.add_argument("--release", action="store_true", help="gera também .xz e .sha256")
    args = ap.parse_args()

    t0 = time.time()
    if not args.no_download:
        download(args.raw_dir)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if os.path.exists(args.out):
        os.remove(args.out)

    conn = sqlite3.connect(args.out)
    conn.executescript(SCHEMA_SQL)
    example_sentences = build_jmdict(conn, args.raw_dir)
    build_sentences(conn, args.raw_dir, example_sentences)
    build_kanji(conn, args.raw_dir)
    conn.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("schema_version", str(SCHEMA_VERSION)),
        ("built_at", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("jmdict_simplified", JMDICT_TAG),
        ("kanjivg", KANJIVG_TAG),
        ("tatoeba_export", "per_language, baixado em " + datetime.date.today().isoformat()),
    ])
    log("criando índices...")
    conn.executescript(INDEX_SQL)
    conn.commit()
    conn.execute("ANALYZE")
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    size = os.path.getsize(args.out)
    log(f"ok: {args.out} ({size / 1e6:.1f} MB) em {time.time() - t0:.0f}s")

    if args.release:
        xz = args.out + ".xz"
        log("compactando (xz)...")
        with open(args.out, "rb") as src, lzma.open(xz, "wb", preset=6) as dst:
            for chunk in iter(lambda: src.read(1 << 20), b""):
                dst.write(chunk)
        digest = sha256_of(xz)
        with open(xz + ".sha256", "w") as f:
            f.write(f"{digest}  {os.path.basename(xz)}\n")
        log(f"ok: {xz} ({os.path.getsize(xz) / 1e6:.1f} MB), sha256 {digest}")


if __name__ == "__main__":
    main()
