"""Conversões de kana e leituras do KANJIDIC2. Sem dependências do Anki."""
import html


def kata_to_hira(text):
    """Katakana (U+30A1-U+30F6) -> hiragana. O ー e o que não for katakana ficam como estão."""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def hira_to_kata(text):
    """Hiragana (U+3041-U+3096) -> katakana. O ー e o que não for hiragana ficam como estão."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in text)


def to_script(text, script):
    """Converte uma leitura para 'hiragana' ou 'katakana'."""
    return hira_to_kata(text) if script == "katakana" else kata_to_hira(text)


def split_okurigana(kun):
    """'た.べる' -> ('た', 'べる'); 'みず-' -> ('みず', ''); '-ぎ' -> ('ぎ', '').

    O ponto separa a raiz do okurigana no KANJIDIC2; o hífen marca prefixo ou sufixo.
    """
    kun = kun.strip("-")
    root, _dot, okuri = kun.partition(".")
    return root, okuri


def kun_html(kun):
    """Leitura kun em HTML: raiz em destaque, okurigana em cinza claro."""
    root, okuri = split_okurigana(kun_to_hira(kun))
    out = f'<span class="raiz">{html.escape(root)}</span>'
    if okuri:
        out += f'<span class="okuri">{html.escape(okuri)}</span>'
    return out


def kun_to_hira(kun):
    return kata_to_hira(kun)
