import re

import pytest

from addon import stroke_svg

# 日 (4 traços) simplificado no estilo do KanjiVG
HI = [
    "M31.5,24.5c1.62,0.38,3.31,0.38,5,0.38c15,0,29.5-1.38,42.5-1.38c2.66,0,4.54,1.54,4.54,4.62",
    "M31.62,25.5c0.62,3.5,0.5,48.62,0.5,61",
    "M32.5,56.5c13.5,0,35.5-1.5,48-1.5",
    "M33,87.5c14.5-0.5,35-1,47.5-1",
]


def test_path_info_inicio_e_comprimento():
    x, y, length = stroke_svg.path_info("M10,20L40,60")
    assert (x, y) == (10, 20)
    assert length == pytest.approx(50)


def test_path_info_relativo_e_curvas():
    x, y, length = stroke_svg.path_info(HI[1])
    assert (x, y) == (31.62, 25.5)
    assert 55 < length < 70  # traço quase reto de ~61 de altura


def test_path_info_s_e_h_v():
    _x, _y, length = stroke_svg.path_info("M0,0H10V10h-10v-10")
    assert length == pytest.approx(40)
    stroke_svg.path_info("M10,10c5,0,10,5,10,10s5,10,10,10")


def test_comando_desconhecido_da_erro():
    with pytest.raises(ValueError):
        stroke_svg.path_info("M0,0A5,5,0,0,1,10,10")


def test_svg_tem_um_path_animado_e_um_numero_por_traco():
    svg = stroke_svg.build_kanji_svg("日", HI)
    assert svg.startswith('<svg class="kk k65e5"')
    assert len(re.findall(r'<path class="p\d+"', svg)) == 4
    assert len(re.findall(r'<text class="n\d+"', svg)) == 4
    for n in range(1, 5):
        assert f"@keyframes k65e5p{n}" in svg and f"@keyframes k65e5n{n}" in svg


def test_svg_usa_variaveis_css_para_funcionar_no_escuro():
    svg = stroke_svg.build_kanji_svg("日", HI)
    assert "var(--traco-atual)" in svg and "var(--traco-feito)" in svg
    assert "#" not in svg.split("<style>")[1].split("</style>")[0]  # nenhuma cor fixa nas animações


def test_duracao_total_inclui_pausa_final():
    svg = stroke_svg.build_kanji_svg("日", HI)
    total = float(re.search(r"animation:k65e5p1 ([\d.]+)s linear infinite", svg).group(1))
    durs = stroke_svg.stroke_durations([stroke_svg.path_info(d)[2] for d in HI])
    esperado = sum(durs) + 4 * stroke_svg.INTERVALO + stroke_svg.PAUSA_FINAL
    assert total == pytest.approx(esperado, abs=0.01)


def test_percentuais_dos_keyframes_crescem_e_ficam_em_0_100():
    svg = stroke_svg.build_kanji_svg("日", HI)
    for block in re.findall(r"@keyframes k65e5p\d+\{(.*?)\}\}", svg):
        pcts = [float(p) for p in re.findall(r"([\d.]+)%", block)]
        assert pcts == sorted(pcts) and pcts[0] == 0 and pcts[-1] == 100


def test_build_strokes_html_um_svg_por_kanji_distinto():
    paths = {"日": HI}
    html = stroke_svg.build_strokes_html("日日本る", paths.get)
    assert html.count("<svg") == 1  # 本 sem dados é ignorado; 日 repetido só uma vez
    assert stroke_svg.build_strokes_html("きれい", paths.get) == ""
