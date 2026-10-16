"""HTML dos campos gerados (KanjiInfo, Significado). Sem dependências do Anki.

As classes CSS (.ki, .selo, .raiz, .okuri...) estão em templates/style.css.
"""
import html

from . import kana

# O KANJIDIC2 usa a escala antiga do JLPT (4 níveis); só 4 e 3 casam 1:1 com N5 e N4.
_JLPT = {4: "N5", 3: "N4", 2: "N3–N2", 1: "N2–N1"}


def jlpt_label(jlpt_old):
    return _JLPT.get(jlpt_old, "")


def kanji_info_html(k, onyomi_script="hiragana", max_meanings=4):
    """Bloco de um kanji: kun, on, traços, radical, JLPT e significado.

    `k` é o dicionário devolvido por lookup.get_kanji.
    """
    e = html.escape
    linhas = []
    if k["kun"]:
        kuns = "・".join(kana.kun_html(r) for r in k["kun"])
        linhas.append(f'<div class="ki-linha"><span class="selo">訓</span><span>{kuns}</span></div>')
    if k["on"]:
        ons = "・".join(e(kana.to_script(r, onyomi_script)) for r in k["on"])
        linhas.append(f'<div class="ki-linha"><span class="selo">音</span><span>{ons}</span></div>')
    meta = []
    # a contagem do KanjiVG casa com a animação (em 108 kanji difere da do KANJIDIC2, ex.: 逢 10 x 11)
    strokes = len(k["stroke_paths"]) if k.get("stroke_paths") else k["strokes"]
    if strokes:
        meta.append(f"{strokes}画")
    if k["radical"]:
        meta.append(f'部首 {e(k["radical"])}')
    jlpt = jlpt_label(k["jlpt_old"])
    if jlpt:
        meta.append(jlpt)
    if meta:
        linhas.append(f'<div class="ki-meta">{" · ".join(meta)}</div>')
    meanings = k["meanings_pt"] or k["meanings_en"]
    if meanings:
        linhas.append(f'<div class="ki-sig">{e(", ".join(meanings[:max_meanings]))}</div>')
    return (
        f'<div class="ki"><div class="ki-glifo">{e(k["literal"])}</div>'
        f'<div class="ki-corpo">{"".join(linhas)}</div></div>'
    )


def senses_html(senses):
    """Lista numerada de acepções (o CSS troca os números por ❶ ❷ ❸)."""
    e = html.escape
    itens = []
    for s in senses:
        txt = e("; ".join(s["gloss"]))
        extra = [x for x in s.get("info", [])]
        if extra:
            txt += f' <span class="nota">({e("; ".join(extra))})</span>'
        itens.append(f"<li>{txt}</li>")
    return f'<ol>{"".join(itens)}</ol>'
