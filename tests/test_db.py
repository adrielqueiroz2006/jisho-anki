"""Testes do banco (Fase 1). Precisam de build/dicionario.sqlite; senão são pulados."""
import os
import time

import pytest

from addon import kana, lookup
from conftest import ROOT

DB = os.path.join(ROOT, "build", "dicionario.sqlite")

pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="rode tools/build_db.py antes")


@pytest.fixture(scope="module")
def conn():
    return lookup.open_db(DB)


@pytest.mark.parametrize("word", ["食べる", "日本", "水", "きれい", "生"])
def test_consulta_rapida(conn, word):
    t = time.perf_counter()
    entries = lookup.find_entries(conn, word)
    for c in word:
        lookup.get_kanji(conn, c)
    assert entries
    assert (time.perf_counter() - t) * 1000 < 50


def test_taberu_tags_e_glosa(conn):
    e = lookup.find_entries(conn, "食べる")[0]
    assert e["senses"][0]["pos"] == ["v1", "vt"]
    assert e["senses"][0]["gloss"][0] == "to eat"
    assert e["kana"][0]["t"] == "たべる"


def test_busca_por_kana_acha_forma_com_kanji(conn):
    assert any(k["t"] == "食べる" for e in lookup.find_entries(conn, "たべる") for k in e["kanji"])


def test_busca_katakana_equivale_a_hiragana(conn):
    assert lookup.find_entries(conn, "タベル") == lookup.find_entries(conn, "たべる")


def test_homografos_de_sei(conn):
    assert len(lookup.find_entries(conn, "生")) > 1


def test_kanji_info(conn):
    k = lookup.get_kanji(conn, "食")
    assert k["strokes"] == 9 and k["radical"] == "食" and k["jlpt_old"] == 4
    assert "ショク" in k["on"] and "た.べる" in k["kun"]
    assert len(k["stroke_paths"]) == 9


def test_kanji_agua_tem_pt(conn):
    assert "água" in lookup.get_kanji(conn, "水")["meanings_pt"]


@pytest.mark.parametrize("lit,n", [("日", 4), ("水", 4), ("書", 10), ("必", 5), ("鬱", 29)])
def test_tracos_kanjivg(conn, lit, n):
    assert len(lookup.get_kanji(conn, lit)["stroke_paths"]) == n


def test_exemplo_tem_frase_e_traducao(conn):
    ex = lookup.find_entries(conn, "食べる")[0]["examples"][0]
    assert ex["jpn"] and (ex["por"] or ex["eng"])


def test_conversao_kana():
    assert kana.kata_to_hira("ショク") == "しょく"
    assert kana.kata_to_hira("コーヒー") == "こーひー"
