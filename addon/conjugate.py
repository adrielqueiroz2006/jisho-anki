"""Tabelas de conjugação: 13 formas dos verbos e as formas dos adjetivos い e な. Sem dependências do Anki.

O grupo do verbo vem sempre das tags do JMdict, nunca da terminação: 帰る, 入る, 走る, 知る, 切る
parecem ichidan mas são godan (`v5r`).

A palavra escrita e a leitura são conjugadas em paralelo com as mesmas regras, para o furigana de
cada forma sair alinhado (来る: こない, きた, こよう, こられる...).

Uso:
    table = conjugate(word, reading, tags)   # tags de classe gramatical do JMdict; None se não houver tabela
    html = table_html(table)
"""
import html as _html
from dataclasses import dataclass
from typing import Optional

from . import furigana


@dataclass
class Form:
    written: str
    reading: str
    alt_written: Optional[str] = None   # forma alternativa, mostrada em cinza (書かせられる ao lado de 書かされる)
    alt_reading: Optional[str] = None


@dataclass
class Row:
    jp: str
    pt: str
    form: Optional[Form]   # None = a forma não existe para este verbo (mostra "—")
    uso: str
    aviso: str = ""


@dataclass
class Table:
    kind: str              # "verbo" | "adj-i" | "adj-na"
    rows: list


# (nome em japonês, nome em português, uso) das 13 formas, na ordem do PLAN.md
VERB_FORMS = [
    ("辞書形", "dicionário", "forma básica, informal"),
    ("ます形", "polida", "presente/futuro educado"),
    ("ない形", "negativa", "negação informal (“não …”)"),
    ("た形", "passado", "passado informal"),
    ("なかった形", "passado negativo", "negação no passado (“não … (antes)”)"),
    ("て形", "conectiva", "ligar frases, pedidos, ～ている"),
    ("意向形", "volitiva", "“vamos …”, intenção"),
    ("可能形", "potencial", "“conseguir …”, poder"),
    ("受身形", "passiva", "“ser …do” (passiva)"),
    ("使役形", "causativa", "“fazer/deixar …”"),
    ("使役受身形", "causativa-passiva", "“ser obrigado a …”"),
    ("仮定形", "condicional ば", "“se …”"),
    ("命令形", "imperativa", "ordem direta"),
]

ADJ_I_FORMS = [
    ("辞書形", "dicionário", "forma básica, informal"),
    ("丁寧形", "polida", "presente educado"),
    ("否定形", "negativa", "“não é …”"),
    ("否定丁寧", "negativa polida", "“não é …” educado"),
    ("過去形", "passado", "“era …”"),
    ("過去丁寧", "passado polido", "“era …” educado"),
    ("過去否定", "passado negativo", "“não era …”"),
    ("過去否定丁寧", "passado negativo polido", "“não era …” educado"),
    ("て形", "conectiva", "ligar frases (“…, e …”)"),
    ("副詞形", "adverbial", "modifica verbos (“…mente”)"),
    ("条件 ば", "condicional ば", "“se for …”"),
    ("条件 たら", "condicional たら", "“quando/se for …”"),
    ("名詞化", "substantivação", "〜さ: “o quão … é”"),
]

ADJ_NA_FORMS = [
    ("辞書形", "dicionário", "forma básica, informal"),
    ("連体形", "antes de substantivo", "liga o adjetivo ao substantivo (“… + な + coisa”)"),
    ("丁寧形", "polida", "presente educado"),
    ("否定形", "negativa", "“não é …”"),
    ("否定丁寧", "negativa polida", "“não é …” educado"),
    ("過去形", "passado", "“era …”"),
    ("過去丁寧", "passado polido", "“era …” educado"),
    ("過去否定", "passado negativo", "“não era …”"),
    ("過去否定丁寧", "passado negativo polido", "“não era …” educado"),
    ("て形", "conectiva", "ligar frases (“…, e …”)"),
    ("副詞形", "adverbial", "modifica verbos (“…mente”)"),
    ("条件", "condicional", "“se for …”"),
    ("条件 たら", "condicional たら", "“quando/se for …”"),
    ("名詞化", "substantivação", "〜さ: “o quão … é”"),
]

SAME_FORM_NOTE = "mesma forma, o contexto decide"

# terminação do godan -> (a, i, e, o, て, た)
_GODAN = {
    "う": ("わ", "い", "え", "お", "って", "った"),
    "く": ("か", "き", "け", "こ", "いて", "いた"),
    "ぐ": ("が", "ぎ", "げ", "ご", "いで", "いだ"),
    "す": ("さ", "し", "せ", "そ", "して", "した"),
    "つ": ("た", "ち", "て", "と", "って", "った"),
    "ぬ": ("な", "に", "ね", "の", "んで", "んだ"),
    "ぶ": ("ば", "び", "べ", "ぼ", "んで", "んだ"),
    "む": ("ま", "み", "め", "も", "んで", "んだ"),
    "る": ("ら", "り", "れ", "ろ", "って", "った"),
}


class Unsupported(ValueError):
    """A palavra não tem tabela (grupo verbal arcaico, texto que não bate com a tag...)."""


# ---------------------------------------------------------------- grupo do verbo

def verb_kind(tags):
    """('ichidan'|'godan'|'kuru'|'suru', tag que decide) a partir das tags do JMdict, ou None."""
    for t in tags:
        if t in ("v1", "v1-s"):
            return "ichidan", t
        if t.startswith("v5") and t != "v5uru":
            return "godan", t
        if t == "vk":
            return "kuru", t
        if t in ("vs", "vs-i", "vs-s", "vs-c"):
            return "suru", t
    return None


# ---------------------------------------------------------------- motores (uma string por vez)
# Cada motor recebe a forma de dicionário (escrita OU leitura) e devolve 13 itens:
# (principal, alternativa) ou None quando a forma não existe.

def _ichidan(text, tag):
    if not text.endswith("る"):
        raise Unsupported(f"{text}: ichidan sem る final")
    s = text[:-1]
    return [
        (text, None), (s + "ます", None), (s + "ない", None), (s + "た", None), (s + "なかった", None),
        (s + "て", None), (s + "よう", None), (s + "られる", None), (s + "られる", None),
        (s + "させる", None), (s + "させられる", None), (s + "れば", None),
        ((s if tag == "v1-s" else s + "ろ"), None),   # くれる -> くれ
    ]


def _godan(text, tag):
    end = text[-1:]
    if end not in _GODAN:
        raise Unsupported(f"{text}: terminação godan desconhecida")
    s = text[:-1]
    a, i, e, o, te, ta = _GODAN[end]
    if tag == "v5k-s":                    # 行く: 行って, 行った
        te, ta = "って", "った"
    elif tag == "v5u-s":                  # 問う: 問うて, 問うた
        te, ta = "うて", "うた"
    honorific = tag == "v5aru"            # くださる, いらっしゃる, おっしゃる, なさる: ます/命令 com い
    masu_stem = s + ("い" if honorific else i)
    imperative = s + ("い" if honorific else e)

    if tag == "v5r-i":                    # ある: negativa ない; sem potencial, passiva, causativa nem imperativo
        nai_base = text[:-2] if text.endswith(("ある", "有る", "在る")) else s
        nai = nai_base + "ない"
        return [
            (text, None), (masu_stem + "ます", None), (nai, None), (s + ta, None), (nai_base + "なかった", None),
            (s + te, None), (s + o + "う", None), None, None, None, None, (s + e + "ば", None), None,
        ]

    nai = s + a + "ない"
    long_cp = s + a + "せられる"
    short_cp = s + a + "される"
    # す-ending: só a forma longa (話させられる); os demais: curta como principal e longa em cinza
    caus_pass = (long_cp, None) if end == "す" else (short_cp, long_cp)
    return [
        (text, None), (masu_stem + "ます", None), (nai, None), (s + ta, None), (s + a + "なかった", None),
        (s + te, None), (s + o + "う", None), (s + e + "る", None), (s + a + "れる", None),
        (s + a + "せる", None), caus_pass, (s + e + "ば", None), (imperative, None),
    ]


def _suru(text, tag):
    if not text.endswith("する"):
        raise Unsupported(f"{text}: verbo com する que não termina em する")
    p = text[:-2]
    return [
        (text, None), (p + "します", None), (p + "しない", None), (p + "した", None), (p + "しなかった", None),
        (p + "して", None), (p + "しよう", None), (p + "できる", None), (p + "される", None),
        (p + "させる", None), (p + "させられる", None), (p + "すれば", None), (p + "しろ", p + "せよ"),
    ]


def _kuru(text, tag):
    if text.endswith("来る"):
        kana = False
    elif text.endswith("くる"):
        kana = True
    else:
        raise Unsupported(f"{text}: verbo vk que não termina em 来る/くる")
    p = text[:-2]

    def s(kanji, hira):
        return p + (hira if kana else kanji)

    return [
        (text, None), (s("来", "き") + "ます", None), (s("来", "こ") + "ない", None), (s("来", "き") + "た", None),
        (s("来", "こ") + "なかった", None), (s("来", "き") + "て", None), (s("来", "こ") + "よう", None),
        (s("来", "こ") + "られる", None), (s("来", "こ") + "られる", None), (s("来", "こ") + "させる", None),
        (s("来", "こ") + "させられる", None), (s("来", "く") + "れば", None), (s("来", "こ") + "い", None),
    ]


_ENGINES = {"ichidan": _ichidan, "godan": _godan, "suru": _suru, "kuru": _kuru}


# ---------------------------------------------------------------- adjetivos

def _adj_i(text, tag):
    if not text.endswith("い"):
        raise Unsupported(f"{text}: adjetivo い sem い final")
    if tag == "adj-ix":                    # いい/良い: as formas flexionadas usam よ-
        s = text[:-2] + "よ" if text.endswith("いい") else text[:-1]
    else:
        s = text[:-1]
    return [
        (text, None), (text + "です", None), (s + "くない", None), (s + "くないです", s + "くありません"),
        (s + "かった", None), (s + "かったです", None), (s + "くなかった", None),
        (s + "くなかったです", s + "くありませんでした"), (s + "くて", None), (s + "く", None),
        (s + "ければ", None), (s + "かったら", None), (s + "さ", None),
    ]


def _adj_na(text, tag):
    return [
        (text, None), (text + "な", None), (text + "です", None), (text + "ではない", text + "じゃない"),
        (text + "ではありません", text + "じゃありません"), (text + "だった", None), (text + "でした", None),
        (text + "ではなかった", text + "じゃなかった"),
        (text + "ではありませんでした", text + "じゃありませんでした"), (text + "で", None), (text + "に", None),
        (text + "ならば", text + "なら"), (text + "だったら", None), (text + "さ", None),
    ]


# ---------------------------------------------------------------- API

def _build(defs, written_forms, reading_forms, same_form_rows=()):
    rows = []
    for idx, ((jp, pt, uso), w, r) in enumerate(zip(defs, written_forms, reading_forms)):
        if w is None or r is None:
            rows.append(Row(jp, pt, None, uso))
            continue
        form = Form(w[0], r[0], w[1], r[1])
        rows.append(Row(jp, pt, form, uso, SAME_FORM_NOTE if idx in same_form_rows else ""))
    return rows


def conjugate(word, reading, tags):
    """Tabela de `word` (escrita) com `reading` (hiragana) segundo as tags do JMdict; None se não houver.

    Para verbos com する (勉強する) passe a palavra inteira e a leitura inteira; só o する é conjugado.
    """
    try:
        return _conjugate(word, reading, tags)
    except Unsupported:
        return None


def _conjugate(word, reading, tags):
    kind = verb_kind(tags)
    if kind:
        group, tag = kind
        engine = _ENGINES[group]
        w, r = engine(word, tag), engine(reading, tag)
        # 可能形 e 受身形 coincidem no ichidan e no 来る
        same = (7, 8) if group in ("ichidan", "kuru") else ()
        return Table("verbo", _build(VERB_FORMS, w, r, same))
    if "adj-i" in tags or "adj-ix" in tags:
        tag = "adj-ix" if "adj-ix" in tags else "adj-i"
        return Table("adj-i", _build(ADJ_I_FORMS, _adj_i(word, tag), _adj_i(reading, tag)))
    if "adj-na" in tags:
        return Table("adj-na", _build(ADJ_NA_FORMS, _adj_na(word, "adj-na"), _adj_na(reading, "adj-na")))
    return None


# ---------------------------------------------------------------- HTML

def _ruby(written, reading):
    return furigana.to_ruby(furigana.word_furigana(written, reading))


def table_html(table):
    """Tabela pronta para o campo Conjugação (o template a põe dentro de um <details>)."""
    e = _html.escape
    body = []
    for row in table.rows:
        head = f'<th>{e(row.jp)}<span class="aviso">{e(row.pt)}</span></th>'
        if row.form is None:
            body.append(f'<tr>{head}<td class="forma nada">—</td><td class="uso">{e(row.uso)}</td></tr>')
            continue
        f = row.form
        cell = _ruby(f.written, f.reading)
        if f.alt_written:
            cell += f' <span class="alt">{_ruby(f.alt_written, f.alt_reading)}</span>'
        uso = e(row.uso) + (f'<span class="aviso">{e(row.aviso)}</span>' if row.aviso else "")
        body.append(f'<tr>{head}<td class="forma">{cell}</td><td class="uso">{uso}</td></tr>')
    return f'<table class="conj-tab" data-tipo="{table.kind}"><tbody>{"".join(body)}</tbody></table>'
