"""Conjugação: as 13 formas de cada verbo da lista de validação, comparadas com respostas fixas."""
import pytest

from addon import conjugate as cj

# ordem: 辞書 ます ない た なかった て 意向 可能 受身 使役 使役受身 仮定 命令
# cada item: (palavra, leitura, tags, escrita das 13 formas, leitura das 13 formas)
# None = a forma não existe; "a|b" = principal e alternativa (cinza)
VERBS = [
    ("食べる", "たべる", ["v1", "vt"],
     "食べる 食べます 食べない 食べた 食べなかった 食べて 食べよう 食べられる 食べられる 食べさせる 食べさせられる 食べれば 食べろ",
     "たべる たべます たべない たべた たべなかった たべて たべよう たべられる たべられる たべさせる たべさせられる たべれば たべろ"),
    ("書く", "かく", ["v5k", "vt"],
     "書く 書きます 書かない 書いた 書かなかった 書いて 書こう 書ける 書かれる 書かせる 書かされる|書かせられる 書けば 書け",
     "かく かきます かかない かいた かかなかった かいて かこう かける かかれる かかせる かかされる|かかせられる かけば かけ".replace("かけば", "かけば")),
    ("泳ぐ", "およぐ", ["v5g", "vi"],
     "泳ぐ 泳ぎます 泳がない 泳いだ 泳がなかった 泳いで 泳ごう 泳げる 泳がれる 泳がせる 泳がされる|泳がせられる 泳げば 泳げ",
     "およぐ およぎます およがない およいだ およがなかった およいで およごう およげる およがれる およがせる およがされる|およがせられる およげば およげ"),
    ("話す", "はなす", ["v5s", "vt"],
     "話す 話します 話さない 話した 話さなかった 話して 話そう 話せる 話される 話させる 話させられる 話せば 話せ",
     "はなす はなします はなさない はなした はなさなかった はなして はなそう はなせる はなされる はなさせる はなさせられる はなせば はなせ"),
    ("待つ", "まつ", ["v5t", "vt", "vi"],
     "待つ 待ちます 待たない 待った 待たなかった 待って 待とう 待てる 待たれる 待たせる 待たされる|待たせられる 待てば 待て",
     "まつ まちます またない まった またなかった まって まとう まてる またれる またせる またされる|またせられる まてば まて"),
    ("死ぬ", "しぬ", ["v5n", "vi"],
     "死ぬ 死にます 死なない 死んだ 死ななかった 死んで 死のう 死ねる 死なれる 死なせる 死なされる|死なせられる 死ねば 死ね",
     "しぬ しにます しなない しんだ しななかった しんで しのう しねる しなれる しなせる しなされる|しなせられる しねば しね"),
    ("遊ぶ", "あそぶ", ["v5b", "vi"],
     "遊ぶ 遊びます 遊ばない 遊んだ 遊ばなかった 遊んで 遊ぼう 遊べる 遊ばれる 遊ばせる 遊ばされる|遊ばせられる 遊べば 遊べ",
     "あそぶ あそびます あそばない あそんだ あそばなかった あそんで あそぼう あそべる あそばれる あそばせる あそばされる|あそばせられる あそべば あそべ"),
    ("帰る", "かえる", ["v5r", "vi"],   # parece ichidan, é godan
     "帰る 帰ります 帰らない 帰った 帰らなかった 帰って 帰ろう 帰れる 帰られる 帰らせる 帰らされる|帰らせられる 帰れば 帰れ",
     "かえる かえります かえらない かえった かえらなかった かえって かえろう かえれる かえられる かえらせる かえらされる|かえらせられる かえれば かえれ"),
    ("行く", "いく", ["v5k-s", "vi"],   # 行って, não 行いて
     "行く 行きます 行かない 行った 行かなかった 行って 行こう 行ける 行かれる 行かせる 行かされる|行かせられる 行けば 行け",
     "いく いきます いかない いった いかなかった いって いこう いける いかれる いかせる いかされる|いかせられる いけば いけ"),
    ("ある", "ある", ["v5r-i", "vi"],   # negativa ない; o resto não existe
     "ある あります ない あった なかった あって あろう - - - - あれば -",
     "ある あります ない あった なかった あって あろう - - - - あれば -"),
    ("する", "する", ["vs-i", "vi", "vt"],
     "する します しない した しなかった して しよう できる される させる させられる すれば しろ|せよ",
     "する します しない した しなかった して しよう できる される させる させられる すれば しろ|せよ"),
    ("来る", "くる", ["vk", "vi"],   # a leitura muda em cada forma
     "来る 来ます 来ない 来た 来なかった 来て 来よう 来られる 来られる 来させる 来させられる 来れば 来い",
     "くる きます こない きた こなかった きて こよう こられる こられる こさせる こさせられる くれば こい"),
    ("勉強する", "べんきょうする", ["vs", "vt"],
     "勉強する 勉強します 勉強しない 勉強した 勉強しなかった 勉強して 勉強しよう 勉強できる 勉強される 勉強させる 勉強させられる 勉強すれば 勉強しろ|勉強せよ",
     "べんきょうする べんきょうします べんきょうしない べんきょうした べんきょうしなかった べんきょうして べんきょうしよう べんきょうできる べんきょうされる べんきょうさせる べんきょうさせられる べんきょうすれば べんきょうしろ|べんきょうせよ"),
    ("いらっしゃる", "いらっしゃる", ["v5aru", "vi"],   # ます e 命令 com い
     "いらっしゃる いらっしゃいます いらっしゃらない いらっしゃった いらっしゃらなかった いらっしゃって いらっしゃろう いらっしゃれる いらっしゃられる いらっしゃらせる いらっしゃらされる|いらっしゃらせられる いらっしゃれば いらっしゃい",
     "いらっしゃる いらっしゃいます いらっしゃらない いらっしゃった いらっしゃらなかった いらっしゃって いらっしゃろう いらっしゃれる いらっしゃられる いらっしゃらせる いらっしゃらされる|いらっしゃらせられる いらっしゃれば いらっしゃい"),
    # honoríficos e exceções além da lista
    ("くださる", "くださる", ["v5aru", "vt"],
     "くださる くださいます くださらない くださった くださらなかった くださって くださろう くだされる くださられる くださらせる くださらされる|くださらせられる くだされば ください",
     "くださる くださいます くださらない くださった くださらなかった くださって くださろう くだされる くださられる くださらせる くださらされる|くださらせられる くだされば ください"),
    ("おっしゃる", "おっしゃる", ["v5aru", "vt"],
     "おっしゃる おっしゃいます おっしゃらない おっしゃった おっしゃらなかった おっしゃって おっしゃろう おっしゃれる おっしゃられる おっしゃらせる おっしゃらされる|おっしゃらせられる おっしゃれば おっしゃい",
     "おっしゃる おっしゃいます おっしゃらない おっしゃった おっしゃらなかった おっしゃって おっしゃろう おっしゃれる おっしゃられる おっしゃらせる おっしゃらされる|おっしゃらせられる おっしゃれば おっしゃい"),
    ("なさる", "なさる", ["v5aru", "vt"],
     "なさる なさいます なさらない なさった なさらなかった なさって なさろう なされる なさられる なさらせる なさらされる|なさらせられる なされば なさい",
     "なさる なさいます なさらない なさった なさらなかった なさって なさろう なされる なさられる なさらせる なさらされる|なさらせられる なされば なさい"),
    ("買う", "かう", ["v5u", "vt"],
     "買う 買います 買わない 買った 買わなかった 買って 買おう 買える 買われる 買わせる 買わされる|買わせられる 買えば 買え",
     "かう かいます かわない かった かわなかった かって かおう かえる かわれる かわせる かわされる|かわせられる かえば かえ"),
    ("問う", "とう", ["v5u-s", "vt"],   # 問うて, 問うた
     "問う 問います 問わない 問うた 問わなかった 問うて 問おう 問える 問われる 問わせる 問わされる|問わせられる 問えば 問え",
     "とう といます とわない とうた とわなかった とうて とおう とえる とわれる とわせる とわされる|とわせられる とえば とえ"),
    ("読む", "よむ", ["v5m", "vt"],
     "読む 読みます 読まない 読んだ 読まなかった 読んで 読もう 読める 読まれる 読ませる 読まされる|読ませられる 読めば 読め",
     "よむ よみます よまない よんだ よまなかった よんで よもう よめる よまれる よませる よまされる|よませられる よめば よめ"),
    ("見る", "みる", ["v1", "vt"],
     "見る 見ます 見ない 見た 見なかった 見て 見よう 見られる 見られる 見させる 見させられる 見れば 見ろ",
     "みる みます みない みた みなかった みて みよう みられる みられる みさせる みさせられる みれば みろ"),
    ("くれる", "くれる", ["v1-s", "vt"],   # imperativo くれ
     "くれる くれます くれない くれた くれなかった くれて くれよう くれられる くれられる くれさせる くれさせられる くれれば くれ",
     "くれる くれます くれない くれた くれなかった くれて くれよう くれられる くれられる くれさせる くれさせられる くれれば くれ"),
    ("持って来る", "もってくる", ["vk", "vt"],   # composto: só o 来る muda
     "持って来る 持って来ます 持って来ない 持って来た 持って来なかった 持って来て 持って来よう 持って来られる 持って来られる 持って来させる 持って来させられる 持って来れば 持って来い",
     "もってくる もってきます もってこない もってきた もってこなかった もってきて もってこよう もってこられる もってこられる もってこさせる もってこさせられる もってくれば もってこい"),
]


def _parse(spec):
    out = []
    for item in spec.split():
        if item == "-":
            out.append(None)
        else:
            main, _sep, alt = item.partition("|")
            out.append((main, alt or None))
    return out


def _forms(table):
    return [None if r.form is None else (r.form.written, r.form.alt_written) for r in table.rows]


def _readings(table):
    return [None if r.form is None else (r.form.reading, r.form.alt_reading) for r in table.rows]


@pytest.mark.parametrize("word,reading,tags,written,readings", VERBS, ids=[v[0] for v in VERBS])
def test_as_13_formas(word, reading, tags, written, readings):
    table = cj.conjugate(word, reading, tags)
    assert table.kind == "verbo" and len(table.rows) == 13
    assert _forms(table) == _parse(written)
    assert _readings(table) == _parse(readings)


def test_nomes_das_13_formas_na_ordem_do_plano():
    table = cj.conjugate("食べる", "たべる", ["v1", "vt"])
    assert [r.jp for r in table.rows] == [
        "辞書形", "ます形", "ない形", "た形", "なかった形", "て形", "意向形", "可能形", "受身形", "使役形",
        "使役受身形", "仮定形", "命令形"]


def test_o_grupo_vem_da_tag_e_nao_da_terminacao():
    # 帰る/入る/走る/知る/切る terminam em る mas são godan: não podem virar 帰れば→帰れば via ichidan
    for word, reading in [("帰る", "かえる"), ("入る", "はいる"), ("走る", "はしる"), ("知る", "しる"), ("切る", "きる")]:
        t = cj.conjugate(word, reading, ["v5r", "vi"])
        assert t.rows[2].form.written == word[:-1] + "らない"      # 帰らない, não 帰ない
        assert t.rows[5].form.written == word[:-1] + "って"
    t = cj.conjugate("食べる", "たべる", ["v1"])
    assert t.rows[2].form.written == "食べない"


def test_te_e_ta_de_todos_os_godan():
    for dict_form, te, ta in [("買う", "って", "った"), ("待つ", "って", "った"), ("取る", "って", "った"),
                              ("読む", "んで", "んだ"), ("遊ぶ", "んで", "んだ"), ("死ぬ", "んで", "んだ"),
                              ("書く", "いて", "いた"), ("泳ぐ", "いで", "いだ"), ("話す", "して", "した")]:
        tag = "v5" + {"う": "u", "つ": "t", "る": "r", "む": "m", "ぶ": "b", "ぬ": "n", "く": "k", "ぐ": "g", "す": "s"}[dict_form[-1]]
        t = cj.conjugate(dict_form, dict_form, [tag])   # a leitura é igual à escrita: serve para a regra
        assert t.rows[5].form.written == dict_form[:-1] + te, dict_form
        assert t.rows[3].form.written == dict_form[:-1] + ta, dict_form


def test_ichidan_potencial_e_passiva_iguais_levam_a_nota():
    t = cj.conjugate("食べる", "たべる", ["v1"])
    assert t.rows[7].form.written == t.rows[8].form.written == "食べられる"
    assert t.rows[7].aviso == t.rows[8].aviso == cj.SAME_FORM_NOTE
    assert all(r.aviso == "" for i, r in enumerate(t.rows) if i not in (7, 8))


def test_godan_nao_tem_a_nota_de_formas_iguais():
    t = cj.conjugate("書く", "かく", ["v5k"])
    assert all(r.aviso == "" for r in t.rows)


def test_causativa_passiva_godan_curta_principal_e_longa_em_cinza():
    f = cj.conjugate("書く", "かく", ["v5k"]).rows[10].form
    assert (f.written, f.alt_written) == ("書かされる", "書かせられる")


def test_causativa_passiva_dos_verbos_em_su_so_tem_a_longa():
    f = cj.conjugate("話す", "はなす", ["v5s"]).rows[10].form
    assert (f.written, f.alt_written) == ("話させられる", None)


def test_verbo_com_suru_conjuga_so_o_suru_e_o_potencial_vira_dekiru():
    t = cj.conjugate("勉強する", "べんきょうする", ["vs"])
    assert t.rows[7].form.written == "勉強できる"
    assert t.rows[1].form.written == "勉強します"


def test_kuru_mostra_a_leitura_de_cada_forma():
    t = cj.conjugate("来る", "くる", ["vk"])
    assert [r.form.reading for r in t.rows[2:4]] == ["こない", "きた"]
    assert t.rows[6].form.reading == "こよう" and t.rows[7].form.reading == "こられる"
    html = cj.table_html(t)
    assert "<ruby>来<rt>こ</rt></ruby>ない" in html and "<ruby>来<rt>き</rt></ruby>た" in html


def test_kuru_digitado_em_kana():
    t = cj.conjugate("くる", "くる", ["vk"])
    assert [r.form.written for r in t.rows[:4]] == ["くる", "きます", "こない", "きた"]


def test_ichidan_com_imperativo_irregular():
    assert cj.conjugate("くれる", "くれる", ["v1-s"]).rows[12].form.written == "くれ"


def test_ha_verbo_sem_tabela():
    assert cj.conjugate("為る", "する", ["v5uru"]) is None          # grupo não suportado
    assert cj.conjugate("日本", "にほん", ["n"]) is None
    assert cj.conjugate("食べ", "たべ", ["v1"]) is None             # texto que não bate com a tag


def test_formas_inexistentes_viram_traco():
    html = cj.table_html(cj.conjugate("ある", "ある", ["v5r-i"]))
    assert html.count('class="forma nada"') == 5   # potencial, passiva, causativa, causativa-passiva, imperativa


# ---- adjetivos ----

ADJ_I = [
    ("高い", "たかい", ["adj-i"],
     "高い 高いです 高くない 高くないです|高くありません 高かった 高かったです 高くなかった 高くなかったです|高くありませんでした 高くて 高く 高ければ 高かったら 高さ"),
    ("大きい", "おおきい", ["adj-i"],
     "大きい 大きいです 大きくない 大きくないです|大きくありません 大きかった 大きかったです 大きくなかった 大きくなかったです|大きくありませんでした 大きくて 大きく 大きければ 大きかったら 大きさ"),
    ("いい", "いい", ["adj-ix"],   # いい usa よ- nas flexões
     "いい いいです よくない よくないです|よくありません よかった よかったです よくなかった よくなかったです|よくありませんでした よくて よく よければ よかったら よさ"),
    ("良い", "いい", ["adj-ix"],
     "良い 良いです 良くない 良くないです|良くありません 良かった 良かったです 良くなかった 良くなかったです|良くありませんでした 良くて 良く 良ければ 良かったら 良さ"),
    ("かっこいい", "かっこいい", ["adj-ix"],
     "かっこいい かっこいいです かっこよくない かっこよくないです|かっこよくありません かっこよかった かっこよかったです かっこよくなかった かっこよくなかったです|かっこよくありませんでした かっこよくて かっこよく かっこよければ かっこよかったら かっこよさ"),
    ("ない", "ない", ["adj-i"],
     "ない ないです なくない なくないです|なくありません なかった なかったです なくなかった なくなかったです|なくありませんでした なくて なく なければ なかったら なさ"),
]

ADJ_NA = [
    ("静か", "しずか", ["adj-na"],
     "静か 静かな 静かです 静かではない|静かじゃない 静かではありません|静かじゃありません 静かだった 静かでした 静かではなかった|静かじゃなかった 静かではありませんでした|静かじゃありませんでした 静かで 静かに 静かならば|静かなら 静かだったら 静かさ"),
    ("きれい", "きれい", ["adj-na"],
     "きれい きれいな きれいです きれいではない|きれいじゃない きれいではありません|きれいじゃありません きれいだった きれいでした きれいではなかった|きれいじゃなかった きれいではありませんでした|きれいじゃありませんでした きれいで きれいに きれいならば|きれいなら きれいだったら きれいさ"),
    ("綺麗", "きれい", ["adj-na", "n"],
     "綺麗 綺麗な 綺麗です 綺麗ではない|綺麗じゃない 綺麗ではありません|綺麗じゃありません 綺麗だった 綺麗でした 綺麗ではなかった|綺麗じゃなかった 綺麗ではありませんでした|綺麗じゃありませんでした 綺麗で 綺麗に 綺麗ならば|綺麗なら 綺麗だったら 綺麗さ"),
]


@pytest.mark.parametrize("word,reading,tags,written", ADJ_I, ids=[a[0] for a in ADJ_I])
def test_adjetivos_i(word, reading, tags, written):
    t = cj.conjugate(word, reading, tags)
    assert t.kind == "adj-i" and len(t.rows) == 13
    assert _forms(t) == _parse(written)


@pytest.mark.parametrize("word,reading,tags,written", ADJ_NA, ids=[a[0] for a in ADJ_NA])
def test_adjetivos_na(word, reading, tags, written):
    t = cj.conjugate(word, reading, tags)
    assert t.kind == "adj-na" and len(t.rows) == 14
    assert _forms(t) == _parse(written)


def test_leitura_dos_adjetivos_acompanha_a_escrita():
    t = cj.conjugate("良い", "いい", ["adj-ix"])
    assert [r.form.reading for r in t.rows[:3]] == ["いい", "いいです", "よくない"]
    assert "<ruby>良<rt>よ</rt></ruby>くない" in cj.table_html(t)


def test_adjetivo_i_com_texto_que_nao_termina_em_i():
    assert cj.conjugate("高", "たか", ["adj-i"]) is None


# ---- HTML ----

def test_html_tem_uma_linha_por_forma_com_ruby_e_alternativa_em_cinza():
    html = cj.table_html(cj.conjugate("書く", "かく", ["v5k", "vt"]))
    assert html.count("<tr>") == 13 and html.startswith('<table class="conj-tab"')
    assert "<ruby>書<rt>か</rt></ruby>かされる" in html
    assert '<span class="alt"><ruby>書<rt>か</rt></ruby>かせられる</span>' in html
    assert "<th>辞書形<span class=\"aviso\">dicionário</span></th>" in html


def test_html_escapa_o_texto():
    t = cj.Table("verbo", [cj.Row("<b>", "x", cj.Form("a<", "a"), "u&")])
    html = cj.table_html(t)
    assert "&lt;b&gt;" in html and "u&amp;" in html


def test_to_ruby_igual_ao_filtro_do_anki():
    from addon import furigana
    assert furigana.to_ruby("食[た]べる") == "<ruby>食<rt>た</rt></ruby>べる"
    assert furigana.to_ruby("もっと 果物[くだもの]を") == "もっと<ruby>果物<rt>くだもの</rt></ruby>を"
