import os

import pytest

from addon import audio, tts
from addon import notetype as nt

CFG = {"gerar_audio": True, "tts_voice": "ja-JP-NanamiNeural", "tts_backends": ["edge", "gtts"]}
FAKE_MP3 = b"\xff\xf3\x84\xc4" + b"\x00" * 200


def _fields():
    return {nt.F_PALAVRA: "生", nt.F_LEITURA: "なま", nt.F_EXEMPLO: "生の魚は好きじゃない。"}


def test_nome_deterministico_e_depende_do_texto_e_da_voz():
    a = audio.audio_name("なま", "ja-JP-NanamiNeural")
    assert a == audio.audio_name("なま", "ja-JP-NanamiNeural")
    assert a != audio.audio_name("せい", "ja-JP-NanamiNeural")
    assert a != audio.audio_name("なま", "ja-JP-KeitaNeural")
    assert a.startswith("jisho_") and a.endswith(".mp3") and a == a.lower()


def test_palavra_e_falada_pela_leitura_e_a_frase_pelo_texto():
    jobs = audio.plan_jobs(_fields(), CFG)
    assert [(j.field, j.text, j.kind) for j in jobs] == [
        (nt.F_AUDIO_PALAVRA, "なま", "word"), (nt.F_EXEMPLO_AUDIO, "生の魚は好きじゃない。", "example")]


def test_sem_leitura_fala_a_palavra():
    f = {nt.F_PALAVRA: "きれい", nt.F_EXEMPLO: ""}
    assert [j.text for j in audio.plan_jobs(f, CFG)] == ["きれい"]


def test_nao_sobrescreve_audio_existente_sem_regerar():
    existing = {nt.F_AUDIO_PALAVRA: "[sound:meu.mp3]", nt.F_EXEMPLO_AUDIO: ""}
    assert [j.field for j in audio.plan_jobs(_fields(), CFG, existing)] == [nt.F_EXEMPLO_AUDIO]
    assert len(audio.plan_jobs(_fields(), CFG, existing, overwrite=True)) == 2


def test_audio_desligado_na_config():
    assert audio.plan_jobs(_fields(), {**CFG, "gerar_audio": False}) == []


def test_valores_dos_campos():
    assert audio.field_value("word", "a.mp3") == "[sound:a.mp3]"
    v = audio.field_value("example", "b.mp3")
    assert v == '<audio controls preload="none" src="b.mp3"></audio>' and "autoplay" not in v


def test_run_jobs_sintetiza_e_reaproveita_o_cache(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tts, "synthesize", lambda text, cfg: (calls.append(text), (FAKE_MP3, "edge"))[1])
    jobs = audio.plan_jobs(_fields(), CFG)
    (tmp_path / jobs[1].filename).write_bytes(FAKE_MP3)  # a frase já está na mídia
    r = audio.run_jobs(jobs, CFG, str(tmp_path))
    assert calls == ["なま"] and list(r.files) == [jobs[0].filename] and not r.errors


def test_run_jobs_texto_igual_nao_sintetiza_duas_vezes(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tts, "synthesize", lambda text, cfg: (calls.append(text), (FAKE_MP3, "edge"))[1])
    j = audio.Job(nt.F_AUDIO_PALAVRA, "x", "jisho_x.mp3", "word")
    audio.run_jobs([j, j], CFG, str(tmp_path))
    assert calls == ["x"]


def test_run_jobs_sem_internet_para_de_tentar(tmp_path, monkeypatch):
    calls = []

    def boom(text, cfg):
        calls.append(text)
        raise tts.TtsError("sem internet")

    monkeypatch.setattr(tts, "synthesize", boom)
    jobs = [audio.Job("f", f"t{i}", f"jisho_{i}.mp3", "word") for i in range(5)]
    r = audio.run_jobs(jobs, CFG, str(tmp_path))
    assert len(calls) == 2 and not r.files and len(r.errors) == 5
    assert audio.summarize_errors(r).startswith("Sem áudio: ")


def test_run_jobs_chama_o_progresso(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "synthesize", lambda text, cfg: (FAKE_MP3, "edge"))
    seen = []
    audio.run_jobs([audio.Job("f", "a", "jisho_a.mp3", "word")], CFG, str(tmp_path), lambda d, t: seen.append((d, t)))
    assert seen == [(0, 1), (1, 1)]


def test_apply_result_grava_a_midia_e_devolve_os_campos(tmp_path):
    jobs = audio.plan_jobs(_fields(), CFG)
    result = audio.AudioResult(files={jobs[0].filename: FAKE_MP3})  # a frase falhou
    written = []

    def write(name, data):
        written.append(name)
        (tmp_path / name).write_bytes(data)
        return name

    values = audio.apply_result(jobs, result, str(tmp_path), write)
    assert written == [jobs[0].filename]
    assert values == {nt.F_AUDIO_PALAVRA: f"[sound:{jobs[0].filename}]"}  # sem campo para a frase que falhou


def test_apply_result_arquivo_ja_em_cache_vira_campo(tmp_path):
    jobs = audio.plan_jobs(_fields(), CFG)
    (tmp_path / jobs[0].filename).write_bytes(FAKE_MP3)
    values = audio.apply_result(jobs, audio.AudioResult(), str(tmp_path), lambda n, d: n)
    assert nt.F_AUDIO_PALAVRA in values and nt.F_EXEMPLO_AUDIO not in values


def test_apply_result_nome_diferente_do_pedido_e_erro(tmp_path):
    jobs = audio.plan_jobs(_fields(), CFG)[:1]
    r = audio.AudioResult(files={jobs[0].filename: FAKE_MP3})
    assert audio.apply_result(jobs, r, str(tmp_path), lambda n, d: "outro.mp3") == {}
    assert r.errors


def test_looks_like_mp3():
    assert tts.looks_like_mp3(FAKE_MP3) and tts.looks_like_mp3(b"ID3" + b"\x00" * 200)
    assert not tts.looks_like_mp3(b"<html>" + b"x" * 200) and not tts.looks_like_mp3(b"\xff\xf3")


def test_ordem_de_backends_e_fallback(monkeypatch):
    from addon.tts import edge, gtts

    def fail(*a, **k):
        raise tts.TtsError("fora do ar")

    monkeypatch.setattr(edge, "synthesize", fail)
    monkeypatch.setattr(gtts, "synthesize", lambda text: FAKE_MP3)
    data, name = tts.synthesize("たべる", CFG)
    assert name == "gtts" and data == FAKE_MP3
    data, name = tts.synthesize("たべる", {**CFG, "tts_backends": ["gtts", "edge"]})
    assert name == "gtts"


def test_todos_os_backends_falham_junta_os_motivos(monkeypatch):
    from addon.tts import edge, gtts

    monkeypatch.setattr(edge, "synthesize", lambda *a, **k: (_ for _ in ()).throw(tts.TtsError("A")))
    monkeypatch.setattr(gtts, "synthesize", lambda t: b"nao e mp3" * 50)
    with pytest.raises(tts.TtsError) as e:
        tts.synthesize("x", CFG)
    assert "edge: A" in str(e.value) and "gtts" in str(e.value) and "MP3" in str(e.value)


def test_backend_desconhecido():
    with pytest.raises(tts.TtsError, match="desconhecido"):
        tts.synthesize("x", {"tts_backends": ["nenhum"]})


@pytest.mark.skipif(not os.environ.get("JISHO_LIVE"), reason="usa a internet; rode com JISHO_LIVE=1")
@pytest.mark.parametrize("backend", ["edge", "gtts"])
def test_ao_vivo(backend):
    data, name = tts.synthesize("たべる", {"tts_backends": [backend]})
    assert name == backend and tts.looks_like_mp3(data) and len(data) > 2000
