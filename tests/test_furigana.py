import os
import tempfile

import pytest

from addon import furigana


def test_alinhamento_kanji_e_okurigana():
    assert furigana.align("食べ", "タベ") == [("食", "た"), ("べ", None)]
    assert furigana.align("振り返る", "ふりかえる") == [("振", "ふ"), ("り", None), ("返", "かえ"), ("る", None)]


def test_alinhamento_so_kanji_e_so_kana():
    assert furigana.align("日本", "にほん") == [("日本", "にほん")]
    assert furigana.align("きれい", "きれい") == [("きれい", None)]


def test_alinhamento_que_nao_bate_cai_na_palavra_inteira():
    assert furigana.align("食べる", "ぜんぜんちがう") == [("食べる", "ぜんぜんちがう")]


def test_furigana_da_palavra():
    assert furigana.word_furigana("食べる", "たべる") == "食[た]べる"
    assert furigana.word_furigana("勉強する", "べんきょうする") == "勉強[べんきょう]する"
    assert furigana.word_furigana("来る", "くる") == "来[く]る"
    assert furigana.word_furigana("きれい", "きれい") == "きれい"


def test_frase_com_alvo_destacado_e_espaco_antes_do_kanji():
    out = furigana.sentence_furigana("もっと果物を食べるべきです。", ["食べる"], "食べる")
    assert out == "もっと 果物[くだもの]を<b> 食[た]べる</b>べきです。"


def test_alvo_flexionado_vem_da_dica_do_jmdict():
    out = furigana.sentence_furigana("僕は脚本家で食べていく決心をした。", ["食べる"], "食べて")
    assert "<b> 食[た]べて</b>" in out


def test_alvo_sem_dica_acha_pela_forma_base():
    out = furigana.sentence_furigana("毎朝パンを食べます。", ["食べる"])
    assert "<b> 食[た]べ" in out


def test_frase_sem_alvo_nao_tem_b():
    assert "<b>" not in furigana.sentence_furigana("今日は晴れです。", ["猫"])


def test_html_da_frase_e_escapado():
    assert "&lt;" in furigana.sentence_furigana("1 < 2", [])


def test_formato_e_o_que_o_filtro_do_anki_espera():
    """O filtro furigana do Anki trata o espaço como início da base; confere com o motor real."""
    anki_collection = pytest.importorskip("anki.collection")
    with tempfile.TemporaryDirectory() as d:
        col = anki_collection.Collection(os.path.join(d, "t.anki2"))
        try:
            m = col.models.by_name("Basic")
            m["tmpls"][0]["qfmt"] = "{{furigana:Front}}"
            col.models.update_dict(m)
            n = col.new_note(m)
            n["Front"] = furigana.sentence_furigana("もっと果物を食べるべきです。", ["食べる"], "食べる")
            col.add_note(n, 1)
            html = n.cards()[0].question()
        finally:
            col.close()
    assert "<ruby><rb>果物</rb><rt>くだもの</rt></ruby>" in html
    assert "<ruby><rb>食</rb><rt>た</rt></ruby>" in html
    assert "もっと果物" not in html  # もっと fica fora do ruby
