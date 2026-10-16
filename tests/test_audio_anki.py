"""O áudio nas notas, com o motor real do Anki (pacote `anki`)."""
import pytest

anki_collection = pytest.importorskip("anki.collection")

from addon import audio  # noqa: E402
from addon import notetype as nt  # noqa: E402


@pytest.fixture()
def col(tmp_path):
    c = anki_collection.Collection(str(tmp_path / "t.anki2"))
    yield c
    c.close()


def _card(col, **fields):
    m = nt.ensure_notetype(col)
    n = col.new_note(m)
    for k, v in fields.items():
        n[k] = v
    col.add_note(n, col.decks.id("T"))
    return n.cards()[0]


def test_palavra_toca_na_frente_com_o_arquivo(col):
    c = _card(col, **{nt.F_PALAVRA: "食べる", nt.F_AUDIO_PALAVRA: audio.field_value("word", "jisho_a1b2.mp3")})
    tags = c.question_av_tags()
    assert [type(t).__name__ for t in tags] == ["SoundOrVideoTag"] and tags[0].filename == "jisho_a1b2.mp3"
    assert "frente-audio" in c.question()


def test_audio_da_frase_nao_toca_sozinho_no_verso(col):
    c = _card(col, **{
        nt.F_PALAVRA: "食べる", nt.F_EXEMPLO: "食べる。",
        nt.F_EXEMPLO_AUDIO: audio.field_value("example", "jisho_c3d4.mp3"),
    })
    # nenhum [sound:] no verso => o Anki não agenda reprodução automática da frase
    assert c.answer_av_tags() == []
    a = c.answer()
    assert '<div class="ex-audio"><audio controls preload="none" src="jisho_c3d4.mp3"></audio></div>' in a


def test_anki_reconhece_o_audio_da_frase_como_midia(col):
    """A verificação de mídia não pode tratar o arquivo como órfão."""
    m = nt.ensure_notetype(col)
    found = col.media.files_in_str(m["id"], audio.field_value("example", "jisho_c3d4.mp3"))
    assert "jisho_c3d4.mp3" in found
    assert "jisho_a1b2.mp3" in col.media.files_in_str(m["id"], audio.field_value("word", "jisho_a1b2.mp3"))


def test_grava_na_midia_com_o_nome_pedido(col):
    name = audio.audio_name("なま", "ja-JP-NanamiNeural")
    assert col.media.write_data(name, b"\xff\xf3" + b"\x00" * 200) == name
    assert col.media.have(name)
