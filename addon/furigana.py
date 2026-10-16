"""Furigana no formato do Anki (`食[た]べる`) para palavras e frases.

A leitura de palavras vem do JMdict; a das frases, do Janome (tokenizador em Python puro, em vendor/).
Sem dependências do Anki.

Formato: o filtro `{{furigana:...}}` do Anki trata como base tudo o que vem entre o espaço (ou o `>`
de uma tag) e o `[`. Por isso cada trecho com kanji leva um espaço antes: `もっと 果物[くだもの]を`.
"""
import html
import os
import re
import sys

from . import kana

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
_KANJI = "一-鿿㐀-䶿々〆ヶ"
_KANJI_RUN = re.compile(f"[{_KANJI}]+")
_tokenizer = None


def has_kanji(text):
    return bool(_KANJI_RUN.search(text))


def get_tokenizer():
    """Carrega o Janome na primeira chamada (leva ~0,5 s e ~120 MB de memória)."""
    global _tokenizer
    if _tokenizer is None:
        if _VENDOR not in sys.path:
            sys.path.append(_VENDOR)
        from janome.tokenizer import Tokenizer

        _tokenizer = Tokenizer()
    return _tokenizer


def align(surface, reading):
    """Divide `surface` em [(texto, leitura ou None)], dando leitura só aos trechos com kanji.

    '食べ','タベ' -> [('食','た'),('べ',None)]. Se os trechos em kana não baterem com a leitura,
    a palavra inteira recebe a leitura.
    """
    reading = kana.kata_to_hira(reading)
    parts, last = [], 0
    for m in _KANJI_RUN.finditer(surface):
        if m.start() > last:
            parts.append((surface[last:m.start()], False))
        parts.append((m.group(), True))
        last = m.end()
    if last < len(surface):
        parts.append((surface[last:], False))
    if not any(is_kanji for _t, is_kanji in parts):
        return [(surface, None)]
    pattern = "".join("(.+?)" if is_kanji else re.escape(kana.kata_to_hira(t)) for t, is_kanji in parts)
    m = re.fullmatch(pattern, reading)
    if not m:
        return [(surface, reading)]
    groups = iter(m.groups())
    return [(t, next(groups) if is_kanji else None) for t, is_kanji in parts]


def _unit(text, reading):
    return f" {text}[{reading}]" if reading else text


def word_furigana(word, reading):
    """'食べる','たべる' -> '食[た]べる'. Palavra só em kana volta como veio."""
    if not has_kanji(word):
        return word
    return "".join(_unit(t, r) for t, r in align(word, reading)).lstrip(" ")


def sentence_units(sentence):
    """Unidades da frase inteira: [(texto, leitura ou None, forma base, nº do token)]."""
    units = []
    for n, tok in enumerate(get_tokenizer().tokenize(sentence)):
        surface = tok.surface
        reading = tok.reading
        if not has_kanji(surface) or reading in (None, "*"):
            units.append((surface, None, tok.base_form, n))
            continue
        for text, r in align(surface, reading):
            units.append((text, r, tok.base_form, n))
    return units


def find_target_span(sentence, units, forms, hint=None):
    """(início, fim) do alvo na frase: primeiro o texto `hint`, depois um token cuja forma base esteja em `forms`."""
    if hint:
        i = sentence.find(hint)
        if i >= 0:
            return i, i + len(hint)
    pos = 0
    for text, _r, base, token in units:
        if base in forms or text in forms:
            # o alvo é o token inteiro (食 + べ), não só a primeira unidade
            length = sum(len(t) for t, _r2, _b, n in units if n == token)
            return pos, pos + length
        pos += len(text)
    return None


def sentence_furigana(sentence, forms=(), hint=None):
    """Frase com furigana no formato do Anki; o alvo vai dentro de <b>…</b>.

    `forms`: formas da palavra no dicionário (para achar o alvo pela forma base);
    `hint`: o trecho exato da frase (vem do JMdict, ex.: 食べて para 食べる).
    """
    units = sentence_units(sentence)
    span = find_target_span(sentence, units, set(forms), hint)
    out, pos, open_b = [], 0, False
    for text, reading, _base, _token in units:
        start, end = pos, pos + len(text)
        pos = end
        inside = span is not None and start < span[1] and end > span[0]
        if inside and not open_b:
            out.append("<b>")
            open_b = True
        elif not inside and open_b:
            out.append("</b>")
            open_b = False
        out.append(_unit(html.escape(text, quote=False), reading))
    if open_b:
        out.append("</b>")
    return "".join(out).lstrip(" ")


_BRACKET = re.compile(r" ?([^ >\[\]]+?)\[(.+?)\]")


def to_ruby(text):
    """Formato de furigana do Anki -> <ruby> pronto (o mesmo que o filtro do Anki faz nos templates).

    Para campos que o template não passa pelo filtro, como a tabela de conjugação.
    """
    return _BRACKET.sub(lambda m: f"<ruby>{m.group(1)}<rt>{m.group(2)}</rt></ruby>", text)
