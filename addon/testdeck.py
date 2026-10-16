"""Deck de teste com as 20 palavras de validação do PLAN.md. Só usa a coleção, não a interface."""
from . import fill
from . import notetype as nt

DECK_NAME = "Jisho Card – Teste"

# (palavra, o que testa)
WORDS = [
    ("食べる", "ichidan, transitivo, caso base"),
    ("書く", "godan く"),
    ("泳ぐ", "godan ぐ"),
    ("話す", "godan す, causativa-passiva longa"),
    ("待つ", "godan つ"),
    ("死ぬ", "godan ぬ"),
    ("遊ぶ", "godan ぶ"),
    ("帰る", "godan com cara de ichidan"),
    ("行く", "exceção 行って"),
    ("ある", "negativa ない"),
    ("する", "irregular"),
    ("来る", "irregular com mudança de leitura"),
    ("勉強する", "verbo com する"),
    ("いらっしゃる", "honorífico"),
    ("日本", "substantivo, dois kanji, leitura especial"),
    ("水", "kanji isolado, significado em pt do KANJIDIC2"),
    ("生", "muitas leituras, janela de escolha"),
    ("きれい", "só kana, adjetivo な, sem bloco de kanji"),
    ("必ず", "ordem de traços pouco intuitiva"),
    ("鬱", "29 traços, animação longa"),
]


def build_test_fields(conn, word, cfg=None):
    """(campos, tags) para `word`, usando sempre a primeira entrada (sem janela). None se não existir."""
    res = fill.resolve_word(conn, word)
    if not res.entries:
        return None
    fields, tags = fill.build_fields(conn, res.word, res.entries[0], cfg, suru=res.suru)
    fields[nt.F_PALAVRA] = res.word
    return fields, tags


def prepare_test_notes(col, conn, cfg=None):
    """Notas que ainda faltam no deck: ([(palavra, campos, tags, o_que_testa)], palavras_não_encontradas)."""
    have = {col.get_note(nid)[nt.F_PALAVRA]
            for nid in col.find_notes(f'"note:{nt.NOTETYPE_NAME}" "deck:{DECK_NAME}"')}
    prepared, missing = [], []
    for word, why in WORDS:
        if word in have:
            continue
        built = build_test_fields(conn, word, cfg)
        if built is None:
            missing.append(word)
        else:
            prepared.append((word, built[0], built[1], why))
    return prepared, missing


def commit_test_notes(col, prepared, audio_values=None):
    """Cria as notas preparadas. `audio_values`: {palavra: {campo: valor}} com o áudio já gravado na mídia."""
    m = nt.ensure_notetype(col)
    deck_id = col.decks.id(DECK_NAME)
    for word, fields, tags, why in prepared:
        note = col.new_note(m)
        for name, value in {**fields, **(audio_values or {}).get(word, {})}.items():
            note[name] = value
        note[nt.F_NOTAS] = f"Teste: {why}"
        note.tags = tags + ["jisho::teste"]
        col.add_note(note, deck_id)
    return len(prepared)


def create_test_deck(col, conn, cfg=None):
    """Versão sem áudio (testes). Devolve (criadas, não_encontradas)."""
    prepared, missing = prepare_test_notes(col, conn, cfg)
    return commit_test_notes(col, prepared), missing
