"""Preenchimento em lote: lógica pura (com o dicionário real) e áudio em paralelo."""
import os
import threading
import time

import pytest

from addon import audio, batch, dbmanager, settings, tts
from addon import notetype as nt
from conftest import ROOT

DB = os.path.join(ROOT, "build", "dicionario.sqlite")
needs_db = pytest.mark.skipif(not os.path.exists(DB), reason="rode tools/build_db.py antes")
CFG = {**settings.defaults(), "gerar_audio": True}


@pytest.fixture(scope="module")
def conn():
    return dbmanager.get_connection(settings.defaults())


def _empty(word, **extra):
    fields = {name: "" for name in nt.FIELDS}
    fields[nt.F_PALAVRA] = word
    fields.update(extra)
    return batch.NoteInput(1, fields, [])


@needs_db
def test_nota_nova_e_preenchida_com_audio_e_tags(conn):
    r = batch.process_note(conn, _empty("食べる"), CFG)
    assert r.status == batch.OK and not r.ambiguous
    assert r.changes[nt.F_LEITURA] == "たべる" and nt.F_CONJUGACAO in r.changes
    assert [j.field for j in r.jobs] == [nt.F_AUDIO_PALAVRA, nt.F_EXEMPLO_AUDIO]
    assert r.jobs[0].text == "たべる"
    assert "jisho::verbo" in r.new_tags


@needs_db
def test_nunca_toca_na_palavra_nem_em_campo_editado(conn):
    inp = _empty("食べる", **{nt.F_SIGNIFICADO: "meu significado", nt.F_NOTAS: "minha nota"})
    r = batch.process_note(conn, inp, CFG)
    assert nt.F_SIGNIFICADO not in r.changes and nt.F_NOTAS not in r.changes and nt.F_PALAVRA not in r.changes


@needs_db
def test_regerar_substitui_menos_palavra_e_notas(conn):
    inp = _empty("食べる", **{nt.F_SIGNIFICADO: "meu significado", nt.F_NOTAS: "minha nota"})
    r = batch.process_note(conn, inp, CFG, overwrite=True)
    assert "<ol>" in r.changes[nt.F_SIGNIFICADO] and nt.F_NOTAS not in r.changes


@needs_db
def test_nota_completa_nao_tem_o_que_fazer(conn):
    first = batch.process_note(conn, _empty("食べる"), {**CFG, "gerar_audio": False})
    full = _empty("食べる", **first.changes)
    again = batch.process_note(conn, batch.NoteInput(1, full.fields, list(first.new_tags)), {**CFG, "gerar_audio": False})
    assert again.status == batch.COMPLETA and not again.changes and not again.jobs


@needs_db
def test_palavra_com_html_e_espaco_do_anki(conn):
    r = batch.process_note(conn, _empty("<div>食べる&nbsp;</div>"), CFG)
    assert r.status == batch.OK and r.word == "食べる"


@needs_db
def test_palavra_vazia_inexistente_e_flexionada(conn):
    assert batch.process_note(conn, _empty("<br>"), CFG).status == batch.VAZIA
    assert batch.process_note(conn, _empty("ぬぬぬぬぬぬ"), CFG).status == batch.NAO_ACHADA
    r = batch.process_note(conn, _empty("食べます"), CFG)
    assert r.status == batch.FLEXIONADA and "食べる" in r.message and not r.changes


@needs_db
def test_homografo_usa_a_primeira_e_avisa(conn):
    r = batch.process_note(conn, _empty("生"), CFG)
    assert r.status == batch.OK and r.ambiguous


@needs_db
def test_leitura_ja_na_nota_escolhe_a_entrada_certa(conn):
    # 生 com leitura せい já preenchida: não é ambíguo, e escolhe a entrada de せい, não a primeira (なま)
    from addon import fill

    r = batch.process_note(conn, _empty("生", **{nt.F_LEITURA: "せい"}), CFG, overwrite=True)
    entries = fill.resolve_word(conn, "生").entries
    sei = next(e for e in entries if any(k["t"] == "せい" for k in e["kana"]))
    expected, _tags = fill.build_fields(conn, "生", sei)
    assert not r.ambiguous
    assert r.changes[nt.F_SIGNIFICADO] == expected[nt.F_SIGNIFICADO]   # significado da entrada せい
    assert nt.F_LEITURA not in r.changes                               # a leitura já era せい: nada a mudar


@needs_db
def test_verbo_com_suru(conn):
    r = batch.process_note(conn, _empty("勉強する"), CFG)
    assert r.status == batch.OK and r.changes[nt.F_LEITURA] == "べんきょうする"


@needs_db
def test_erro_em_uma_nota_nao_derruba_as_outras(conn, monkeypatch):
    from addon import fill

    original = fill.build_fields

    def boom(conn_, word, *a, **k):
        if word == "書く":
            raise RuntimeError("quebrou")
        return original(conn_, word, *a, **k)

    monkeypatch.setattr(fill, "build_fields", boom)
    inputs = [batch.NoteInput(i, _empty(w).fields, []) for i, w in enumerate(["食べる", "書く", "水"])]
    results = batch.process_notes(conn, inputs, CFG)
    assert [r.status for r in results] == [batch.OK, batch.ERRO, batch.OK]
    assert "quebrou" in results[1].message


@needs_db
def test_progresso_e_cancelamento(conn):
    inputs = [batch.NoteInput(i, _empty(w).fields, []) for i, w in enumerate(["食べる", "書く", "水", "日本"])]
    seen = []
    batch.process_notes(conn, inputs, CFG, progress=lambda d, t: seen.append((d, t)))
    assert seen[0] == (0, 4) and seen[-1] == (4, 4)
    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 2          # deixa passar 2 notas
    results = batch.process_notes(conn, inputs, CFG, should_cancel=cancel)
    assert len(results) == 2


def test_relatorio():
    R = batch.NoteResult
    results = [
        R(1, "食べる", batch.OK), R(2, "生", batch.OK, ambiguous=True), R(3, "水", batch.COMPLETA),
        R(4, "ぬぬ", batch.NAO_ACHADA), R(5, "食べます", batch.FLEXIONADA, message="forma flexionada de 食べる"),
        R(6, "", batch.VAZIA), R(7, "書く", batch.ERRO, message="RuntimeError: x"),
    ]
    ar = audio.AudioResult(errors=["“たべる”: sem internet"])
    text = batch.summarize(results, 7, ar)
    assert "2 notas preenchidas ou atualizadas de 7" in text and "1 já estavam completas" in text
    assert "Mais de uma entrada" in text and "生" in text
    assert "Não encontradas no dicionário: ぬぬ" in text
    assert "食べます (→ 食べる)" in text
    assert "1 notas com o campo Palavra vazio" in text and "RuntimeError: x" in text
    assert "Sem áudio: “たべる”: sem internet" in text
    assert "Cancelado: 3 de 9" in batch.summarize(results[:3], 9, None, cancelled=True)


def test_relatorio_limita_listas_longas():
    results = [batch.NoteResult(i, f"語{i}", batch.NAO_ACHADA) for i in range(40)]
    assert "(+25)" in batch.summarize(results, 40)


# ---- áudio em paralelo ----

def test_audio_em_paralelo_respeita_a_ordem_e_usa_varias_threads(tmp_path, monkeypatch):
    threads = set()

    def fake(text, cfg):
        threads.add(threading.get_ident())
        time.sleep(0.05)
        return b"\xff\xf3" + text.encode() * 100, "edge"

    monkeypatch.setattr(tts, "synthesize", fake)
    jobs = [audio.Job("f", f"t{i}", f"jisho_{i}.mp3", "word") for i in range(6)]
    seen = []
    r = audio.run_jobs(jobs, CFG, str(tmp_path), lambda d, t: seen.append(d), workers=3)
    assert sorted(r.files) == sorted(j.filename for j in jobs) and not r.errors
    assert len(threads) > 1 and seen == [0, 1, 2, 3, 4, 5, 6]


def test_audio_cancelado_para_o_resto(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "synthesize", lambda text, cfg: (b"\xff\xf3" + b"x" * 200, "edge"))
    jobs = [audio.Job("f", f"t{i}", f"jisho_{i}.mp3", "word") for i in range(5)]
    r = audio.run_jobs(jobs, CFG, str(tmp_path), should_cancel=lambda: True)
    assert r.cancelled and not r.files and not r.errors
