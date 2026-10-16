from addon import kana


def test_katakana_para_hiragana():
    assert kana.kata_to_hira("ショク") == "しょく"
    assert kana.kata_to_hira("ジキ") == "じき"
    assert kana.kata_to_hira("ヴ") == "ゔ"


def test_prolongamento_e_resto_ficam():
    assert kana.kata_to_hira("コーヒー") == "こーひー"
    assert kana.kata_to_hira("食べる") == "食べる"
    assert kana.kata_to_hira("ヷ") == "ヷ"  # fora de U+30A1-U+30F6


def test_hiragana_para_katakana():
    assert kana.hira_to_kata("たべる") == "タベル"
    assert kana.hira_to_kata("きゃー") == "キャー"


def test_to_script():
    assert kana.to_script("ショク", "hiragana") == "しょく"
    assert kana.to_script("しょく", "katakana") == "ショク"


def test_divisao_de_okurigana():
    assert kana.split_okurigana("た.べる") == ("た", "べる")
    assert kana.split_okurigana("く.らう") == ("く", "らう")
    assert kana.split_okurigana("みず-") == ("みず", "")
    assert kana.split_okurigana("-ぎ") == ("ぎ", "")
    assert kana.split_okurigana("ひ") == ("ひ", "")


def test_kun_html_raiz_em_destaque_e_okurigana_cinza():
    assert kana.kun_html("た.べる") == '<span class="raiz">た</span><span class="okuri">べる</span>'
    assert kana.kun_html("みず-") == '<span class="raiz">みず</span>'
