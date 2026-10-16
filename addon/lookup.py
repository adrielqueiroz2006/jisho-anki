"""Consultas ao dicionario.sqlite (somente leitura).

Não depende do Anki: pode ser usado nos testes e nos scripts de tools/.
"""
import json
import sqlite3

from . import kana


def open_db(path):
    # abre em modo somente leitura; check_same_thread=False porque o Anki consulta em threads de fundo
    uri = "file:" + path.replace("\\", "/").replace("?", "%3F").replace("#", "%23") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _variants(text):
    text = text.strip()
    out = [text]
    for v in (kana.kata_to_hira(text), kana.hira_to_kata(text)):
        if v not in out:
            out.append(v)
    return out


def find_entries(conn, text, max_examples=3):
    """Entradas do JMdict cuja forma (kanji ou kana) é exatamente `text`.

    Ordem: formas comuns primeiro, depois correspondência em kanji antes de kana, depois id.
    Cada resultado: {id, common, kanji, kana, senses, examples, matched_kind}.
    """
    variants = _variants(text)
    marks = ",".join("?" * len(variants))
    rows = conn.execute(
        f"""SELECT e.id, e.common, e.data, MIN(CASE f.kind WHEN 'k' THEN 0 ELSE 1 END)
            FROM form f JOIN entry e ON e.id = f.entry_id
            WHERE f.text IN ({marks})
            GROUP BY e.id
            ORDER BY e.common DESC, 4, e.id""",
        variants,
    ).fetchall()
    results = []
    for eid, common, data, kind in rows:
        d = json.loads(data)
        results.append({
            "id": eid,
            "common": bool(common),
            "kanji": d["k"],
            "kana": d["r"],
            "senses": d["s"],
            "examples": get_examples(conn, eid, max_examples),
            "matched_kind": "k" if kind == 0 else "r",
        })
    return results


def get_examples(conn, entry_id, limit=3):
    """Frases de exemplo da entrada; as que têm tradução em português vêm primeiro."""
    rows = conn.execute(
        """SELECT x.sense_idx, x.word, s.id, s.jpn, s.por, s.eng
           FROM example x JOIN sentence s ON s.id = x.sentence_id
           WHERE x.entry_id = ?
           ORDER BY (s.por IS NULL), length(s.jpn)
           LIMIT ?""",
        (entry_id, limit),
    ).fetchall()
    return [{"sense_idx": r[0], "word": r[1], "id": r[2], "jpn": r[3], "por": r[4], "eng": r[5]}
            for r in rows]


def get_kanji(conn, literal):
    r = conn.execute(
        """SELECT literal, strokes, grade, jlpt_old, freq, radical_num, radical,
                  on_yomi, kun_yomi, meanings_en, meanings_pt, strokes_svg
           FROM kanji WHERE literal = ?""",
        (literal,),
    ).fetchone()
    if not r:
        return None
    return {
        "literal": r[0], "strokes": r[1], "grade": r[2], "jlpt_old": r[3], "freq": r[4],
        "radical_num": r[5], "radical": r[6],
        "on": json.loads(r[7]), "kun": json.loads(r[8]),
        "meanings_en": json.loads(r[9]), "meanings_pt": json.loads(r[10]),
        "stroke_paths": json.loads(r[11]) if r[11] else None,
    }


def get_tags(conn):
    return dict(conn.execute("SELECT code, description FROM tag"))


def _like_pattern(text):
    """Texto literal para LIKE com ESCAPE de barra invertida."""
    esc = "\\"
    text = text.replace(esc, esc * 2).replace("%", esc + "%").replace("_", esc + "_")
    return "%" + text + "%"


def search_sentences(conn, forms, limit=3):
    """Frases do Tatoeba que contêm alguma das `forms`, para palavras sem exemplo no JMdict.

    Prefere as que têm tradução em português, depois as mais curtas. Só aceita frases com tradução.
    """
    out = []
    for form in forms:
        if len(out) >= limit:
            break
        rows = conn.execute(
            r"""SELECT id, jpn, por, eng FROM sentence
                WHERE jpn LIKE ? ESCAPE '\' AND (por IS NOT NULL OR eng IS NOT NULL)
                ORDER BY (por IS NULL), length(jpn) LIMIT ?""",
            (_like_pattern(form), limit),
        ).fetchall()
        for r in rows:
            if all(r[0] != o["id"] for o in out):
                out.append({"sense_idx": None, "word": form, "id": r[0], "jpn": r[1], "por": r[2], "eng": r[3]})
    return out[:limit]
