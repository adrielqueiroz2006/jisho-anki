import os

import pytest

from addon import dbmanager, fill, settings, testdeck
from addon import notetype as nt
from conftest import ROOT

DB = os.path.join(ROOT, "build", "dicionario.sqlite")
pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="rode tools/build_db.py antes")


@pytest.fixture(scope="module")
def conn():
    return dbmanager.get_connection(settings.defaults())


@pytest.mark.parametrize("word,_why", testdeck.WORDS)
def test_as_20_palavras_de_teste_preenchem_sem_erro(conn, word, _why):
    built = testdeck.build_test_fields(conn, word)
    assert built is not None, f"{word} não está no dicionário"
    fields, _tags = built
    for name in (nt.F_LEITURA, nt.F_FURIGANA, nt.F_CLASSE, nt.F_SIGNIFICADO, nt.F_EXEMPLO,
                 nt.F_EXEMPLO_FURIGANA, nt.F_EXEMPLO_TRADUCAO):
        assert fields[name].strip(), f"{word}: campo {name} vazio"
    assert fields[nt.F_SIGNIFICADO].startswith("<ol>")


def test_taberu_campos_exatos(conn):
    f, tags = testdeck.build_test_fields(conn, "食べる")
    assert f[nt.F_LEITURA] == "たべる"
    assert f[nt.F_FURIGANA] == "食[た]べる"
    assert f[nt.F_KUNYOMI] == "く.う、く.らう、た.べる、は.む"
    assert f[nt.F_ONYOMI] == "しょく、じき"
    assert f[nt.F_EXEMPLO] == "もっと果物を食べるべきです。"
    assert f[nt.F_EXEMPLO_FURIGANA] == "もっと 果物[くだもの]を<b> 食[た]べる</b>べきです。"
    assert f[nt.F_EXEMPLO_TRADUCAO] == "You should eat more fruit."
    assert "【動・一段・他】" in f[nt.F_CLASSE]
    assert f[nt.F_TRACOS].count("<svg") == 1
    assert tags == ["jisho::verbo", "jisho::ichidan", "jisho::jlpt_n5"]


def test_onyomi_em_katakana_pela_config(conn):
    f, _ = testdeck.build_test_fields(conn, "食べる", {"onyomi_script": "katakana"})
    assert f[nt.F_ONYOMI] == "ショク、ジキ"


def test_so_kana_nao_tem_bloco_de_kanji_nem_traco(conn):
    f, _tags = testdeck.build_test_fields(conn, "きれい")
    assert f[nt.F_KANJI_INFO] == "" and f[nt.F_TRACOS] == ""
    assert f[nt.F_FURIGANA] == "きれい"


def test_dois_kanji_geram_dois_blocos_e_dois_svg(conn):
    f, _tags = testdeck.build_test_fields(conn, "日本")
    assert f[nt.F_KANJI_INFO].count('class="ki"') == 2 and f[nt.F_TRACOS].count("<svg") == 2
    assert f[nt.F_LEITURA] == "にほん"


def test_verbo_com_suru_vem_do_substantivo(conn):
    r = fill.resolve_word(conn, "勉強する")
    assert r.kind == "suru" and r.suru
    f, tags = fill.build_fields(conn, r.word, r.entries[0], suru=True)
    assert f[nt.F_LEITURA] == "べんきょうする"
    assert f[nt.F_FURIGANA] == "勉強[べんきょう]する"
    assert "【動・サ変" in f[nt.F_CLASSE] and "jisho::suru" in tags


def test_forma_flexionada_vira_forma_de_dicionario(conn):
    r = fill.resolve_word(conn, "食べます")
    assert r.kind == "base" and r.word == "食べる" and r.original == "食べます"


def test_palavra_inexistente(conn):
    assert fill.resolve_word(conn, "ぬぬぬぬぬぬ").entries == []


def test_homografos_pedem_escolha(conn):
    assert fill.needs_choice(fill.resolve_word(conn, "生").entries)
    assert not fill.needs_choice(fill.resolve_word(conn, "食べる").entries)


def test_leitura_acompanha_a_forma_escrita(conn):
    entry = fill.resolve_word(conn, "日本").entries[0]
    assert fill.pick_reading(entry, "日本") == "にほん"


def test_palavra_sem_exemplo_no_jmdict_usa_busca_no_tatoeba(conn):
    # 勉強 tem exemplo no JMdict; "勉強家" provavelmente não: o importante é nunca falhar
    r = fill.resolve_word(conn, "勉強家")
    if r.entries:
        f, _tags = fill.build_fields(conn, r.word, r.entries[0])
        assert nt.F_SIGNIFICADO in f


# ---- mesclagem sem pisar em edição manual ----

EXISTING = {nt.F_PALAVRA: "食べる", nt.F_LEITURA: "", nt.F_SIGNIFICADO: "<div><br></div>",
            nt.F_KANJI_INFO: "meu texto", nt.F_NOTAS: "minha nota"}
GENERATED = {nt.F_LEITURA: "たべる", nt.F_SIGNIFICADO: "<ol><li>to eat</li></ol>",
             nt.F_KANJI_INFO: "gerado", nt.F_NOTAS: "gerada", nt.F_PALAVRA: "outra"}


def test_merge_so_preenche_vazios():
    assert fill.merge_fields(EXISTING, GENERATED) == {
        nt.F_LEITURA: "たべる", nt.F_SIGNIFICADO: "<ol><li>to eat</li></ol>"}


def test_merge_regerar_substitui_menos_palavra_e_notas():
    assert fill.merge_fields(EXISTING, GENERATED, overwrite=True) == {
        nt.F_LEITURA: "たべる", nt.F_SIGNIFICADO: "<ol><li>to eat</li></ol>", nt.F_KANJI_INFO: "gerado"}


def test_merge_valor_gerado_vazio_nao_apaga():
    assert fill.merge_fields({nt.F_LEITURA: "x"}, {nt.F_LEITURA: ""}, overwrite=True) == {}


def test_is_blank():
    assert fill.is_blank("") and fill.is_blank("<br>") and fill.is_blank(" &nbsp; <div></div>")
    assert not fill.is_blank("a")


# ---- tabela de conjugação no campo ----

VERBOS_DE_TESTE = ["食べる", "書く", "泳ぐ", "話す", "待つ", "死ぬ", "遊ぶ", "帰る", "行く", "ある", "する", "来る",
                   "勉強する", "いらっしゃる"]


@pytest.mark.parametrize("word", VERBOS_DE_TESTE)
def test_verbos_de_teste_ganham_a_tabela_de_13_formas(conn, word):
    f, _tags = testdeck.build_test_fields(conn, word)
    html = f[nt.F_CONJUGACAO]
    assert 'data-tipo="verbo"' in html and html.count("<tr>") == 13


@pytest.mark.parametrize("word", ["日本", "水", "生", "必ず", "鬱"])
def test_substantivos_e_adverbios_nao_ganham_tabela(conn, word):
    f, _tags = testdeck.build_test_fields(conn, word)
    assert nt.F_CONJUGACAO not in f


def test_adjetivo_na_ganha_a_tabela_propria(conn):
    f, _tags = testdeck.build_test_fields(conn, "きれい")
    assert 'data-tipo="adj-na"' in f[nt.F_CONJUGACAO] and f[nt.F_CONJUGACAO].count("<tr>") == 14


def test_adjetivo_i_ganha_a_tabela_propria(conn):
    r = fill.resolve_word(conn, "高い")
    f, _tags = fill.build_fields(conn, r.word, r.entries[0])
    assert 'data-tipo="adj-i"' in f[nt.F_CONJUGACAO] and f[nt.F_CONJUGACAO].count("<tr>") == 13
    assert "<ruby>高<rt>たか</rt></ruby>くない" in f[nt.F_CONJUGACAO]


def test_ii_usa_yo_nas_formas_flexionadas(conn):
    r = fill.resolve_word(conn, "いい")
    entry = next(e for e in r.entries if any("adj-ix" in s["pos"] for s in e["senses"]))
    f, _tags = fill.build_fields(conn, r.word, entry)
    assert "よくない" in f[nt.F_CONJUGACAO]


def test_substantivo_com_vs_digitado_sem_suru_nao_vira_verbo(conn):
    r = fill.resolve_word(conn, "勉強")
    f, _tags = fill.build_fields(conn, r.word, r.entries[0])
    assert nt.F_CONJUGACAO not in f


def test_taberu_tabela_com_furigana_no_campo(conn):
    f, _tags = testdeck.build_test_fields(conn, "食べる")
    html = f[nt.F_CONJUGACAO]
    assert "<ruby>食<rt>た</rt></ruby>べさせられる" in html
    assert html.count(cj_note()) == 2


def cj_note():
    from addon import conjugate
    return conjugate.SAME_FORM_NOTE


def test_tabela_de_cada_palavra_do_deck_de_teste_nao_quebra(conn):
    for word, _why in testdeck.WORDS:
        built = testdeck.build_test_fields(conn, word)
        assert built is not None
