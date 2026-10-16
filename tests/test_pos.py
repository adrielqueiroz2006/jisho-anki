from addon import pos


def test_taberu():
    h = pos.pos_html(["v1", "vt"])
    assert "【動・一段・他】" in h and "Verbo ichidan, transitivo" in h and "(v1, vt)" in h


def test_substantivo_e_adjetivo():
    assert "【名】" in pos.pos_html(["n"])
    assert "【形動】" in pos.pos_html(["adj-na"]) and "Adjetivo な" in pos.pos_html(["adj-na"])


def test_tag_desconhecida_e_ignorada():
    assert pos.pos_html(["xyz"]) == ""
    assert "Substantivo" in pos.pos_html(["xyz", "n"])


def test_grupo_do_verbo_vem_da_tag_nunca_da_terminacao():
    assert pos.verb_group(["v5r", "vi"]) == "godan"   # 帰る: parece ichidan, é godan
    assert pos.verb_group(["v1"]) == "ichidan"
    assert pos.verb_group(["vk"]) == "kuru"
    assert pos.verb_group(["vs-i"]) == "suru" and pos.verb_group(["vs"]) == "suru"
    assert pos.verb_group(["v5aru"]) == "godan"
    assert pos.verb_group(["n"]) is None


def test_main_tags_ignora_auxiliar_de_outras_acepcoes():
    senses = [{"pos": ["v5k-s", "vi"]}, {"pos": ["v5k-s", "aux-v"]}, {"pos": ["vt"]}]
    assert pos.main_tags(senses) == ["v5k-s", "vi", "vt"]


def test_is_verb():
    assert pos.is_verb(["v1", "vt"])
    assert not pos.is_verb(["n"])
