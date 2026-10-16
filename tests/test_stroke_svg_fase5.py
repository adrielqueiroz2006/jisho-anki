"""Fase 5: números dos traços, versão estática, contagem de traços e todos os kanji do banco."""
import json
import math
import os
import re

import pytest

from addon import dbmanager, lookup, render, settings, stroke_svg
from conftest import ROOT

HI = [
    "M31.5,24.5c1.62,0.38,3.31,0.38,5,0.38c15,0,29.5-1.38,42.5-1.38c2.66,0,4.54,1.54,4.54,4.62",
    "M31.62,25.5c0.62,3.5,0.5,48.62,0.5,61",
    "M32.5,56.5c13.5,0,35.5-1.5,48-1.5",
    "M33,87.5c14.5-0.5,35-1,47.5-1",
]
DB = os.path.join(ROOT, "build", "dicionario.sqlite")
needs_db = pytest.mark.skipif(not os.path.exists(DB), reason="rode tools/build_db.py antes")


def test_polilinha_comeca_no_inicio_e_termina_no_fim():
    _start, length, pts = stroke_svg._walk("M10,10L50,10")
    assert pts[0] == (10, 10) and pts[-1] == (50, 10) and length == pytest.approx(40)
    assert len(pts) >= 10  # retas também são amostradas


def test_numeros_ficam_dentro_da_moldura_e_um_por_traco():
    spots = stroke_svg.number_positions(HI)
    assert len(spots) == 4
    assert all(3 <= x <= 106 and 3 <= y <= 106 for x, y in spots)


def test_numeros_nao_se_sobrepoem_entre_si():
    spots = stroke_svg.number_positions(HI)
    for i, a in enumerate(spots):
        for b in spots[i + 1:]:
            assert math.hypot(a[0] - b[0], a[1] - b[1]) >= 6


def test_numero_fica_longe_dos_tracos():
    spots = stroke_svg.number_positions(HI)
    pts = [p for d in HI for p in stroke_svg._walk(d)[2]]
    for x, y in spots:
        assert min(math.hypot(x - px, y - py) for px, py in pts) >= 5


def test_versao_estatica_tem_todos_os_tracos_e_numeros_e_nenhuma_animacao():
    svg = stroke_svg.build_kanji_svg("日", HI, animated=False)
    assert "kk-estatico" in svg and "@keyframes" not in svg and "<style" not in svg
    assert len(re.findall(r"<text ", svg)) == 4 and svg.count("<path d=") >= 4


def test_versao_animada_continua_com_animacao():
    assert "@keyframes" in stroke_svg.build_kanji_svg("日", HI)


def test_contagem_de_tracos_do_cartao_vem_do_kanjivg():
    k = {"literal": "逢", "strokes": 10, "stroke_paths": ["M0,0L1,1"] * 11, "kun": [], "on": [],
         "radical": "辶", "jlpt_old": None, "meanings_pt": [], "meanings_en": []}
    assert "11画" in render.kanji_info_html(k)
    assert "10画" in render.kanji_info_html(dict(k, stroke_paths=None))


@needs_db
def test_todos_os_kanji_do_banco_geram_svg_valido():
    conn = lookup.open_db(DB)
    rows = conn.execute("SELECT literal, strokes_svg FROM kanji WHERE strokes_svg IS NOT NULL").fetchall()
    assert len(rows) > 6000
    # a varredura completa leva ~40 s: por padrão 1 em cada 12 (e sempre os mais densos); JISHO_FULL=1 faz todos
    if not os.environ.get("JISHO_FULL"):
        dense = [r for r in rows if len(json.loads(r[1])) >= 25]
        rows = rows[::12] + dense
    for literal, raw in rows:
        paths = json.loads(raw)
        svg = stroke_svg.build_kanji_svg(literal, paths)
        assert svg.count('<path class="p') == len(paths) and svg.count("<text ") == len(paths), literal
        assert len(svg) < 40000, literal  # cabe folgado num campo do Anki


@needs_db
@pytest.mark.parametrize("literal,expected", [("食", 9), ("書", 10), ("日", 4), ("水", 4), ("必", 5), ("鬱", 29)])
def test_kanji_da_lista_de_validacao(literal, expected):
    conn = dbmanager.get_connection(settings.defaults())
    paths = lookup.get_kanji(conn, literal)["stroke_paths"]
    assert len(paths) == expected
    svg = stroke_svg.build_kanji_svg(literal, paths)
    for n in range(1, expected + 1):
        assert f'class="p{n}"' in svg and f"@keyframes k{ord(literal):x}n{n}" in svg
