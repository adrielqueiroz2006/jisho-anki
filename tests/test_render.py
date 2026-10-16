from addon import render

KANJI = {
    "literal": "食", "strokes": 9, "grade": 2, "jlpt_old": 4, "freq": 328, "radical_num": 184, "radical": "食",
    "on": ["ショク", "ジキ"], "kun": ["く.う", "た.べる"], "meanings_en": ["eat", "food"],
    "meanings_pt": ["comer", "comida"], "stroke_paths": None,
}


def test_kanji_info_hiragana_por_padrao():
    h = render.kanji_info_html(KANJI)
    assert "しょく・じき" in h and "ショク" not in h
    assert '<span class="raiz">た</span><span class="okuri">べる</span>' in h
    assert "9画 · 部首 食 · N5" in h


def test_kanji_info_katakana_opcional():
    assert "ショク・ジキ" in render.kanji_info_html(KANJI, onyomi_script="katakana")


def test_significado_em_portugues_do_kanjidic_tem_prioridade():
    assert "comer, comida" in render.kanji_info_html(KANJI)
    k = dict(KANJI, meanings_pt=[])
    assert "eat, food" in render.kanji_info_html(k)


def test_kanji_sem_kun_nao_tem_linha_kun():
    k = dict(KANJI, kun=[])
    assert "訓" not in render.kanji_info_html(k)


def test_html_e_escapado():
    k = dict(KANJI, meanings_pt=["<b>x</b>"])
    assert "<b>x</b>" not in render.kanji_info_html(k)


def test_rotulos_jlpt():
    assert render.jlpt_label(4) == "N5" and render.jlpt_label(3) == "N4"
    assert render.jlpt_label(None) == ""


def test_lista_de_sentidos():
    h = render.senses_html([{"gloss": ["to eat"], "info": []}, {"gloss": ["to live on", "to live off"], "info": ["as ～に"]}])
    assert h.startswith("<ol>") and h.count("<li>") == 2
    assert "to live on; to live off" in h and '<span class="nota">(as ～に)</span>' in h
