"""Cria e atualiza o note type "Jisho Card" e instala as fontes na mídia da coleção.

Só usa a API da coleção (anki.collection), então também roda fora da interface, nos testes.
"""
import os
import re

NOTETYPE_NAME = "Jisho Card"
TEMPLATE_NAME = "Verbete"

# A ordem é a do PLAN.md. Os nomes ficam todos aqui; o resto do código importa as constantes.
F_PALAVRA = "Palavra"
F_LEITURA = "Leitura"
F_FURIGANA = "Furigana"
F_AUDIO_PALAVRA = "ÁudioPalavra"
F_CLASSE = "ClasseGramatical"
F_SIGNIFICADO = "Significado"
F_KANJI_INFO = "KanjiInfo"
F_KUNYOMI = "Kunyomi"
F_ONYOMI = "Onyomi"
F_EXEMPLO = "Exemplo"
F_EXEMPLO_FURIGANA = "ExemploFurigana"
F_EXEMPLO_TRADUCAO = "ExemploTradução"
F_EXEMPLO_AUDIO = "ExemploÁudio"
F_TRACOS = "Traços"
F_CONJUGACAO = "Conjugação"
F_NOTAS = "Notas"

FIELDS = [
    F_PALAVRA, F_LEITURA, F_FURIGANA, F_AUDIO_PALAVRA, F_CLASSE, F_SIGNIFICADO, F_KANJI_INFO,
    F_KUNYOMI, F_ONYOMI, F_EXEMPLO, F_EXEMPLO_FURIGANA, F_EXEMPLO_TRADUCAO, F_EXEMPLO_AUDIO,
    F_TRACOS, F_CONJUGACAO, F_NOTAS,
]

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
_VERSION_RE = re.compile(r"jisho-card:template-v(\d+)")


def _read(*parts):
    with open(os.path.join(ADDON_DIR, *parts), encoding="utf-8") as f:
        return f.read()


def template_version(css):
    m = _VERSION_RE.search(css or "")
    return int(m.group(1)) if m else 0


def install_fonts(col):
    """Copia as fontes (_*.woff2) para collection.media. O prefixo _ as protege da limpeza de mídia.

    Devolve a lista de arquivos escritos. Se o arquivo já existe com outro conteúdo, é substituído.
    """
    fonts_dir = os.path.join(ADDON_DIR, "fonts")
    written = []
    for name in sorted(os.listdir(fonts_dir)):
        if not name.endswith(".woff2"):
            continue
        with open(os.path.join(fonts_dir, name), "rb") as f:
            data = f.read()
        dest = os.path.join(col.media.dir(), name)
        if os.path.exists(dest):
            with open(dest, "rb") as f:
                if f.read() == data:
                    continue
            col.media.trash_files([name])
        used = col.media.write_data(name, data)
        if used != name:
            raise RuntimeError(f"a mídia {name} foi gravada como {used}")
        written.append(name)
    return written


def ensure_notetype(col):
    """Garante que o note type existe, com todos os campos e com os templates atuais.

    Devolve o dicionário do note type. Campos que o usuário acrescentou são preservados;
    os templates e o CSS só são reescritos quando a versão embutida no CSS for mais antiga.
    """
    front, back, css = _read("templates", "front.html"), _read("templates", "back.html"), _read("templates", "style.css")
    install_fonts(col)
    mm = col.models
    m = mm.by_name(NOTETYPE_NAME)
    if m is None:
        m = mm.new(NOTETYPE_NAME)
        for name in FIELDS:
            mm.add_field(m, mm.new_field(name))
        t = mm.new_template(TEMPLATE_NAME)
        t["qfmt"], t["afmt"] = front, back
        mm.add_template(m, t)
        m["css"] = css
        mm.add_dict(m)
        return mm.by_name(NOTETYPE_NAME)

    changed = False
    existing = {f["name"] for f in m["flds"]}
    for name in FIELDS:
        if name not in existing:
            mm.add_field(m, mm.new_field(name))
            changed = True
    if template_version(m["css"]) < template_version(css):
        m["css"] = css
        if m["tmpls"]:
            m["tmpls"][0]["qfmt"], m["tmpls"][0]["afmt"] = front, back
        changed = True
    if changed:
        mm.update_dict(m)
    return mm.by_name(NOTETYPE_NAME)
