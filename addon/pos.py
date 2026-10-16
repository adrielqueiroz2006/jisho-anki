"""Classe gramatical: tags do JMdict -> 【abreviação em japonês】 rótulo em português (tags).

Sem dependências do Anki.
"""
import html

# tag -> (partes da abreviação em japonês, rótulo em português)
_POS = {
    # substantivos e afins
    "n": (("名",), "Substantivo"),
    "n-adv": (("名", "副"), "Substantivo adverbial"),
    "n-t": (("名", "時"), "Substantivo temporal"),
    "n-pr": (("名", "固"), "Nome próprio"),
    "n-suf": (("名", "尾"), "Substantivo usado como sufixo"),
    "n-pref": (("名", "接頭"), "Substantivo usado como prefixo"),
    "pn": (("代",), "Pronome"),
    "ctr": (("助数",), "Contador"),
    "num": (("数",), "Numeral"),
    # adjetivos
    "adj-i": (("形",), "Adjetivo い"),
    "adj-ix": (("形",), "Adjetivo い (いい/よい)"),
    "adj-na": (("形動",), "Adjetivo な"),
    "adj-no": (("連体",), "Substantivo com の (adjetival)"),
    "adj-pn": (("連体",), "Pré-nominal"),
    "adj-t": (("形動",), "Adjetivo たる"),
    "adj-f": (("連体",), "Palavra pré-nominal"),
    "adj-ku": (("形",), "Adjetivo く (arcaico)"),
    "adj-shiku": (("形",), "Adjetivo しく (arcaico)"),
    "adj-nari": (("形動",), "Adjetivo なり (arcaico)"),
    "adj-kari": (("形",), "Adjetivo かり (arcaico)"),
    # advérbios e outros
    "adv": (("副",), "Advérbio"),
    "adv-to": (("副",), "Advérbio com と"),
    "conj": (("接",), "Conjunção"),
    "int": (("感",), "Interjeição"),
    "prt": (("助",), "Partícula"),
    "pref": (("接頭",), "Prefixo"),
    "suf": (("接尾",), "Sufixo"),
    "aux": (("助動",), "Auxiliar"),
    "aux-v": (("助動",), "Verbo auxiliar"),
    "aux-adj": (("助動",), "Adjetivo auxiliar"),
    "cop": (("助動",), "Cópula"),
    "exp": (("連語",), "Expressão"),
    "unc": (("他",), "Não classificada"),
    # verbos
    "v1": (("動", "一段"), "Verbo ichidan"),
    "v1-s": (("動", "一段"), "Verbo ichidan (くれる)"),
    "v5aru": (("動", "五段"), "Verbo godan (ある honorífico)"),
    "v5b": (("動", "五段"), "Verbo godan (ぶ)"),
    "v5g": (("動", "五段"), "Verbo godan (ぐ)"),
    "v5k": (("動", "五段"), "Verbo godan (く)"),
    "v5k-s": (("動", "五段"), "Verbo godan (行く)"),
    "v5m": (("動", "五段"), "Verbo godan (む)"),
    "v5n": (("動", "五段"), "Verbo godan (ぬ)"),
    "v5r": (("動", "五段"), "Verbo godan (る)"),
    "v5r-i": (("動", "五段"), "Verbo godan (る, irregular: ある)"),
    "v5s": (("動", "五段"), "Verbo godan (す)"),
    "v5t": (("動", "五段"), "Verbo godan (つ)"),
    "v5u": (("動", "五段"), "Verbo godan (う)"),
    "v5u-s": (("動", "五段"), "Verbo godan (う, especial)"),
    "v5uru": (("動", "五段"), "Verbo godan (うる)"),
    "vk": (("動", "カ変"), "Verbo irregular 来る"),
    "vs": (("動", "サ変"), "Verbo com する"),
    "vs-i": (("動", "サ変"), "Verbo irregular する"),
    "vs-s": (("動", "サ変"), "Verbo す especial"),
    "vs-c": (("動", "サ変"), "Verbo す (arcaico)"),
    "vz": (("動", "ザ変"), "Verbo ずる"),
    "vn": (("動",), "Verbo irregular ぬ"),
    "vr": (("動",), "Verbo irregular る"),
    "v2": (("動", "二段"), "Verbo nidan (arcaico)"),
    "v4": (("動", "四段"), "Verbo yodan (arcaico)"),
    # transitividade
    "vt": (("他",), "transitivo"),
    "vi": (("自",), "intransitivo"),
}

# prefixos de tags com muitas variantes (v2k-k, v4h...)
_PREFIX = {"v2": "v2", "v4": "v4"}


def _lookup(tag):
    if tag in _POS:
        return _POS[tag]
    for prefix, base in _PREFIX.items():
        if tag.startswith(prefix):
            return _POS[base]
    return None


def is_verb(tags):
    return any(_lookup(t) and _lookup(t)[0][0] == "動" for t in tags)


def verb_group(tags):
    """'ichidan', 'godan', 'kuru', 'suru' ou None, a partir das tags do JMdict (nunca pela terminação)."""
    for t in tags:
        if t in ("v1", "v1-s"):
            return "ichidan"
        if t.startswith("v5"):
            return "godan"
        if t == "vk":
            return "kuru"
        if t in ("vs", "vs-i", "vs-s", "vs-c"):
            return "suru"
    return None


def collect_tags(senses):
    """Tags de classe gramatical de todas as acepções, sem repetir, na ordem em que aparecem."""
    seen = []
    for s in senses:
        for t in s["pos"]:
            if t not in seen:
                seen.append(t)
    return seen


def main_tags(senses):
    """Tags para o cartão: as da primeira acepção, mais transitivo/intransitivo das demais.

    A união de todas as acepções polui (行く viraria "verbo auxiliar", する "sufixo"...).
    """
    tags = list(senses[0]["pos"]) if senses else []
    for s in senses[1:]:
        for t in s["pos"]:
            if t in ("vt", "vi") and t not in tags:
                tags.append(t)
    return tags


def pos_html(tags):
    """`<span class="pos-jp">【動・一段・他】</span>Verbo ichidan, transitivo <span class="pos-tag">(v1, vt)</span>`"""
    jp, pt = [], []
    for t in tags:
        info = _lookup(t)
        if not info:
            continue
        for part in info[0]:
            if part not in jp:
                jp.append(part)
        pt.append(info[1])
    if not pt:
        return ""
    # "Verbo ichidan, transitivo"; só o primeiro rótulo começa com maiúscula
    label = ", ".join(pt)
    return (
        f'<span class="pos-jp">【{"・".join(jp)}】</span>{html.escape(label)} '
        f'<span class="pos-tag">({html.escape(", ".join(tags))})</span>'
    )
