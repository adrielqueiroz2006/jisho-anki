"""Preenchimento de uma nota Jisho Card a partir do dicionário. Sem dependências do Anki.

`resolve_word` acha as entradas candidatas; `build_fields` monta o conteúdo de cada campo;
`merge_fields` decide o que gravar sem pisar em edição manual.
"""
import html
from dataclasses import dataclass, field

from . import conjugate, furigana, kana, lookup, pos, render, stroke_svg
from . import notetype as nt

DEFAULT_CONFIG = {"onyomi_script": "hiragana", "max_acepcoes": 6}

# Campos que o addon nunca sobrescreve, nem no "Regerar"
PROTECTED = {nt.F_PALAVRA, nt.F_NOTAS}


@dataclass
class Resolution:
    """Resultado da busca: `entries` são as candidatas; `word` é a palavra a gravar na nota."""
    entries: list
    word: str
    kind: str = "direct"            # direct | suru | base
    original: str = ""              # o que o usuário digitou, quando kind == "base"
    suru: bool = False
    notes: list = field(default_factory=list)


def resolve_word(conn, word):
    """Procura `word` no dicionário; se não achar, tenta 勉強する -> 勉強 (vs) e formas flexionadas (食べた -> 食べる)."""
    word = word.strip()
    entries = lookup.find_entries(conn, word)
    if entries:
        return Resolution(entries, word)
    if word.endswith("する") and len(word) > 2:
        stem = lookup.find_entries(conn, word[:-2])
        stem = [e for e in stem if any(t.startswith("vs") for s in e["senses"] for t in s["pos"])]
        if stem:
            return Resolution(stem, word, kind="suru", suru=True)
    base = _base_form(word)
    if base and base != word:
        entries = lookup.find_entries(conn, base)
        if entries:
            return Resolution(entries, base, kind="base", original=word)
    return Resolution([], word)


def _base_form(word):
    """Forma de dicionário da primeira palavra de `word` (verbo/adjetivo flexionado), ou None."""
    try:
        tokens = list(furigana.get_tokenizer().tokenize(word))
    except Exception:
        return None
    if not tokens or tokens[0].part_of_speech.split(",")[0] not in ("動詞", "形容詞"):
        return None
    return tokens[0].base_form


def pick_reading(entry, word):
    """Leitura em hiragana da palavra: a primeira que vale para a forma escrita digitada."""
    kana_forms = entry["kana"]
    if furigana.has_kanji(word):
        for r in kana_forms:
            if "*" in r["k"] or word in r["k"] or not r["k"]:
                return kana.kata_to_hira(r["t"])
    for r in kana_forms:
        if kana.kata_to_hira(r["t"]) == kana.kata_to_hira(word):
            return kana.kata_to_hira(r["t"])
    return kana.kata_to_hira(kana_forms[0]["t"])


def entry_label(entry):
    """Texto de uma entrada para a janela de escolha: 食べる【たべる】(v1, vt) to eat"""
    forms = "・".join(k["t"] for k in entry["kanji"][:3])
    reads = "・".join(r["t"] for r in entry["kana"][:2])
    head = f"{forms}【{reads}】" if forms else reads
    s = entry["senses"][0]
    gloss = "; ".join(s["gloss"][:3])
    return f"{head}  ({', '.join(s['pos'])})  {gloss}" + ("   ★" if entry["common"] else "")


def needs_choice(entries):
    """A janela de escolha abre sempre que há 2 ou mais entradas (生, 水, 上手...)."""
    return len(entries) > 1


def _tags_for(word, entry, kanji_rows, group, is_verb):
    tags = []
    if is_verb:
        tags.append("jisho::verbo")
        if group:
            tags.append(f"jisho::{group}")
    levels = [k["jlpt_old"] for k in kanji_rows if k["jlpt_old"]]
    if levels:
        label = render.jlpt_label(min(levels)).lower().replace("–", "-")
        tags.append(f"jisho::jlpt_{label}")
    return tags


def build_fields(conn, word, entry, cfg=None, suru=False, max_examples=1):
    """Conteúdo de cada campo gerado para `word`, a partir de `entry`. Devolve (campos, tags).

    Áudio e conjugação ficam de fora: entram nas fases 4 e 6.
    """
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    stem = word[:-2] if suru else word
    reading = pick_reading(entry, stem)
    if suru:
        reading += "する"

    senses = entry["senses"][: int(cfg["max_acepcoes"])]
    tags_pos = pos.main_tags(entry["senses"])
    if suru:
        # 勉強する: o substantivo vira verbo com する; mantém transitividade, descarta "n"
        tags_pos = ["vs"] + [t for t in tags_pos if t in ("vt", "vi")]

    kanji_rows = []
    for ch in stem:
        k = lookup.get_kanji(conn, ch)
        if k and all(k["literal"] != x["literal"] for x in kanji_rows):
            kanji_rows.append(k)

    forms = [k["t"] for k in entry["kanji"]] + [r["t"] for r in entry["kana"]]
    if suru:
        forms = [f + "する" for f in forms] + forms
    examples = entry["examples"] or lookup.search_sentences(conn, [stem] + forms[:3], 3)
    example = examples[0] if examples else None

    fields = {
        nt.F_LEITURA: reading,
        nt.F_FURIGANA: furigana.word_furigana(word, reading),
        nt.F_CLASSE: pos.pos_html(tags_pos),
        nt.F_SIGNIFICADO: render.senses_html(senses),
        nt.F_KANJI_INFO: "".join(render.kanji_info_html(k, cfg["onyomi_script"]) for k in kanji_rows),
        nt.F_KUNYOMI: "、".join(kana.kata_to_hira(r) for k in kanji_rows for r in k["kun"]),
        nt.F_ONYOMI: "、".join(kana.to_script(r, cfg["onyomi_script"]) for k in kanji_rows for r in k["on"]),
        nt.F_TRACOS: stroke_svg.build_strokes_html(
            stem, lambda c: (lookup.get_kanji(conn, c) or {}).get("stroke_paths")),
    }
    if example:
        fields[nt.F_EXEMPLO] = example["jpn"]
        fields[nt.F_EXEMPLO_FURIGANA] = _example_furigana(example, forms)
        fields[nt.F_EXEMPLO_TRADUCAO] = example["por"] or example["eng"] or ""

    # "vs" sozinho é um substantivo que aceita する (勉強): só vira tabela se a palavra foi digitada com する
    conj_tags = [t for t in tags_pos if not (t == "vs" and not suru)]
    table = conjugate.conjugate(word, reading, conj_tags)
    if table:
        fields[nt.F_CONJUGACAO] = conjugate.table_html(table)

    group = pos.verb_group(tags_pos)
    return fields, _tags_for(word, entry, kanji_rows, group, pos.is_verb(tags_pos))


def _example_furigana(example, forms):
    try:
        return furigana.sentence_furigana(example["jpn"], forms, example.get("word"))
    except Exception:
        # sem furigana é melhor que sem exemplo
        return html.escape(example["jpn"], quote=False)


def is_blank(value):
    """Campo vazio para o Anki: sem texto, ou só tags/espaços (<br>, &nbsp;)."""
    import re
    text = re.sub(r"<[^>]*>|&nbsp;", "", value or "")
    return not text.strip()


def merge_fields(existing, generated, overwrite=False):
    """Campos a gravar: {nome: valor}. Sem `overwrite`, só os que estão vazios na nota.

    Palavra e Notas nunca entram. Valores gerados vazios não apagam nada.
    """
    changes = {}
    for name, value in generated.items():
        if name in PROTECTED or name not in existing or not value:
            continue
        if overwrite or is_blank(existing[name]):
            if existing[name] != value:
                changes[name] = value
    return changes
