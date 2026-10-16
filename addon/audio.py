"""Áudio das notas: o que gerar, com que nome, e como gravar nos campos. Sem dependências do Anki.

Fluxo (a rede fica em `run_jobs`, que roda em segundo plano; a gravação na coleção é do chamador):
  plan_jobs -> run_jobs (thread) -> apply_result (thread principal, grava a mídia e devolve os campos)

O nome do arquivo é determinístico (`jisho_<hash>.mp3`, hash do texto + voz): o mesmo texto nunca
é sintetizado duas vezes, e regerar uma nota reaproveita o arquivo.
"""
import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import fill, tts
from . import notetype as nt

WORD, EXAMPLE = "word", "example"


@dataclass
class Job:
    field: str
    text: str
    filename: str
    kind: str


@dataclass
class AudioResult:
    files: dict = field(default_factory=dict)   # nome -> bytes recém-sintetizados
    errors: list = field(default_factory=list)  # mensagens para o usuário
    cancelled: bool = False                     # o usuário cancelou antes de terminar


def audio_name(text, voice):
    digest = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"jisho_{digest}.mp3"


def field_value(kind, filename):
    """Palavra: `[sound:...]`, que o Anki toca sozinho. Frase: um <audio> com controles, que não toca sozinho."""
    if kind == WORD:
        return f"[sound:{filename}]"
    return f'<audio controls preload="none" src="{filename}"></audio>'


def plan_jobs(fields, cfg, existing=None, overwrite=False):
    """Áudios a gerar para uma nota.

    `fields`: valores já preenchidos (Palavra, Leitura, Exemplo...); `existing`: valores atuais dos
    campos de áudio. Sem `overwrite`, campo de áudio que já tem conteúdo fica como está.
    """
    if not cfg.get("gerar_audio", True):
        return []
    existing = existing or {}
    voice = cfg.get("tts_voice", "ja-JP-NanamiNeural")
    jobs = []
    # a palavra é falada pela leitura em kana: a forma escrita pode ser lida errado (生 = せい ou なま?)
    word_text = (fields.get(nt.F_LEITURA) or fields.get(nt.F_PALAVRA) or "").strip()
    example_text = (fields.get(nt.F_EXEMPLO) or "").strip()
    for fld, text, kind in ((nt.F_AUDIO_PALAVRA, word_text, WORD), (nt.F_EXEMPLO_AUDIO, example_text, EXAMPLE)):
        if text and (overwrite or fill.is_blank(existing.get(fld, ""))):
            jobs.append(Job(fld, text, audio_name(text, voice), kind))
    return jobs


def run_jobs(jobs, cfg, media_dir, progress=None, workers=1, should_cancel=None):
    """Sintetiza o que ainda não está na mídia. Roda fora da thread principal; não mexe na coleção.

    `workers` > 1 sintetiza em paralelo (use 3 em lotes); `should_cancel()` interrompe o que falta.
    Depois de 2 falhas sem nenhum sucesso, desiste do resto (provavelmente sem internet).
    """
    result = AudioResult()
    todo, seen = [], set()
    for job in jobs:
        if job.filename in seen or os.path.exists(os.path.join(media_dir, job.filename)):
            continue
        seen.add(job.filename)
        todo.append(job)
    total = len(todo)
    lock = threading.Lock()
    state = {"ok": 0, "fails": 0}

    def work(job):
        if should_cancel and should_cancel():
            return "cancelado", None
        with lock:
            if state["ok"] == 0 and state["fails"] >= 2:
                return "pulado", None
        try:
            data, _backend = tts.synthesize(job.text, cfg)
        except tts.TtsError as e:
            with lock:
                state["fails"] += 1
            return "erro", str(e)
        with lock:
            state["ok"] += 1
        return "ok", data

    if progress:
        progress(0, total)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [(job, pool.submit(work, job)) for job in todo]
        for done, (job, fut) in enumerate(futures, start=1):
            kind, payload = fut.result()
            if kind == "ok":
                result.files[job.filename] = payload
            elif kind == "erro":
                result.errors.append(f"“{job.text[:20]}”: {payload}")
            elif kind == "pulado":
                result.errors.append(f"“{job.text[:20]}”: pulado")
            else:
                result.cancelled = True
            if progress:
                progress(done, total)
    return result


def apply_result(jobs, result, media_dir, write_data):
    """Grava os MP3 novos na mídia (`write_data(nome, bytes)` devolve o nome usado) e devolve {campo: valor}."""
    values = {}
    for job in jobs:
        name = job.filename
        if name in result.files:
            used = write_data(name, result.files[name])
            if used != name:
                result.errors.append(f"a mídia {name} foi gravada como {used}")
                continue
        elif not os.path.exists(os.path.join(media_dir, name)):
            continue  # a síntese falhou; o campo fica vazio
        values[job.field] = field_value(job.kind, name)
    return values


def summarize_errors(result):
    """Uma linha para o usuário, ou ''."""
    if not result.errors:
        return ""
    first = result.errors[0]
    more = f" (+{len(result.errors) - 1})" if len(result.errors) > 1 else ""
    return f"Sem áudio: {first}{more}"
