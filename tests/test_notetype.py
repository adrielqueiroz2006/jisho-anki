"""Note type com o motor real do Anki (pacote `anki`); pulado se não estiver instalado."""
import os

import pytest

anki_collection = pytest.importorskip("anki.collection")

from addon import notetype as nt  # noqa: E402
from conftest import ROOT  # noqa: E402


@pytest.fixture()
def col(tmp_path):
    c = anki_collection.Collection(str(tmp_path / "t.anki2"))
    yield c
    c.close()


def test_cria_note_type_com_16_campos_na_ordem(col):
    m = nt.ensure_notetype(col)
    assert m["name"] == "Jisho Card"
    assert [f["name"] for f in m["flds"]] == nt.FIELDS
    assert len(nt.FIELDS) == 16
    assert len(m["tmpls"]) == 1


def test_fontes_vao_para_a_midia_com_prefixo_e_minusculas(col):
    nt.ensure_notetype(col)
    files = sorted(os.listdir(col.media.dir()))
    assert files == ["_literata-italic.woff2", "_literata.woff2", "_shipporimincho-bold.woff2", "_shipporimincho-regular.woff2"]


def test_ensure_e_idempotente(col):
    a = nt.ensure_notetype(col)
    b = nt.ensure_notetype(col)
    assert a["id"] == b["id"]
    assert len([n for n in col.models.all_names_and_ids() if n.name == "Jisho Card"]) == 1


def test_campo_extra_do_usuario_e_campo_apagado(col):
    m = nt.ensure_notetype(col)
    col.models.add_field(m, col.models.new_field("MeuCampo"))
    col.models.remove_field(m, m["flds"][nt.FIELDS.index(nt.F_NOTAS)])
    col.models.update_dict(m)
    m = nt.ensure_notetype(col)
    names = [f["name"] for f in m["flds"]]
    assert "MeuCampo" in names and nt.F_NOTAS in names


def test_template_antigo_e_atualizado_e_o_novo_nao_e_tocado(col):
    m = nt.ensure_notetype(col)
    m["css"] = "/* jisho-card:template-v0 */"
    m["tmpls"][0]["qfmt"] = "{{Palavra}} velho"
    col.models.update_dict(m)
    m = nt.ensure_notetype(col)
    assert "velho" not in m["tmpls"][0]["qfmt"] and nt.template_version(m["css"]) >= 1

    m["tmpls"][0]["qfmt"] = "{{Palavra}} editado pelo usuário"
    col.models.update_dict(m)
    assert "editado pelo usuário" in nt.ensure_notetype(col)["tmpls"][0]["qfmt"]


def _note(col, **fields):
    m = nt.ensure_notetype(col)
    n = col.new_note(m)
    for k, v in fields.items():
        n[k] = v
    col.add_note(n, col.decks.id("T"))
    return n.cards()[0]


def test_frente_so_tem_a_palavra(col):
    q = _note(col, **{nt.F_PALAVRA: "食べる", nt.F_LEITURA: "たべる", nt.F_SIGNIFICADO: "<ol><li>to eat</li></ol>"}).question()
    assert "食べる" in q and "to eat" not in q and "たべる" not in q


def test_frente_sem_audio_nao_tem_botao_nem_tts(col):
    # {{tts}} dá "no players found" no Windows sem voz japonesa instalada
    c = _note(col, **{nt.F_PALAVRA: "食べる"})
    assert c.question_av_tags() == []
    assert "<div class=\"frente-audio\"" not in c.question()


def test_frente_com_audio_usa_o_arquivo_e_nao_o_tts(col):
    tags = _note(col, **{nt.F_PALAVRA: "食べる", nt.F_AUDIO_PALAVRA: "[sound:jisho_a1b2.mp3]"}).question_av_tags()
    assert [type(t).__name__ for t in tags] == ["SoundOrVideoTag"]
    assert tags[0].filename == "jisho_a1b2.mp3"


def test_verso_palavra_so_em_kana_nao_tem_bloco_de_kanji(col):
    a = _note(col, **{nt.F_PALAVRA: "きれい", nt.F_LEITURA: "きれい"}).answer()
    assert "漢字" not in a and "例文" not in a and "活用" not in a


def test_verso_completo_mostra_as_secoes(col):
    from addon import dbmanager, settings, testdeck

    if dbmanager.find_db(settings.defaults()) is None:
        pytest.skip("rode tools/build_db.py antes")
    conn = dbmanager.get_connection(settings.defaults())
    fields, _tags = testdeck.build_test_fields(conn, "食べる")
    a = _note(col, **fields).answer()
    for trecho in ("漢字", "例文", "ki-glifo", "<ruby>", 'class="kk k98df"'):
        assert trecho in a
