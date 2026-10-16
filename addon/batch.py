"""Preenchimento em lote: o que fazer com cada nota selecionada no navegador. Sem dependências do Anki.

`process_notes` é puro (recebe os campos de cada nota e devolve o que gravar), então roda em segundo
plano e é testável fora do Anki. A gravação das notas e da mídia é feita por browser.py na thread
principal.
"""
import re
from dataclasses import dataclass, field

from . import audio, fill, kana
from . import notetype as nt

# estados de uma nota no relatório
OK, COMPLETA, VAZIA, NAO_ACHADA, FLEXIONADA, ERRO = "ok", "completa", "vazia", "nao_achada", "flexionada", "erro"


@dataclass
class NoteInput:
    nid: int
    fields: dict
    tags: list = field(default_factory=list)


@dataclass
class NoteResult:
    nid: int
    word: str
    status: str
    changes: dict = field(default_factory=dict)   # campo -> valor novo (sem áudio)
    new_tags: list = field(default_factory=list)
    jobs: list = field(default_factory=list)      # áudios a gerar
    ambiguous: bool = False                       # havia mais de uma entrada; usou uma delas
    message: str = ""


def _plain(html_text):
    return re.sub(r"<[^>]*>", "", html_text or "").replace("&nbsp;", " ").replace("\xa0", " ").strip()


def choose_entry(entries, current_reading):
    """(entrada, ambígua). Com leitura já na nota, fica com a entrada que bate; senão, a primeira."""
    if current_reading:
        for e in entries:
            if any(kana.kata_to_hira(r["t"]) == kana.kata_to_hira(current_reading) for r in e["kana"]):
                return e, False
    return entries[0], len(entries) > 1


def process_note(conn, inp, cfg, overwrite=False):
    word = _plain(inp.fields.get(nt.F_PALAVRA, ""))
    if not word:
        return NoteResult(inp.nid, "", VAZIA, message="campo Palavra vazio")
    try:
        res = fill.resolve_word(conn, word)
        if not res.entries:
            return NoteResult(inp.nid, word, NAO_ACHADA, message="não está no dicionário")
        if res.kind == "base":
            # no lote não trocamos a palavra sozinhos: quem digitou 食べます resolve com o botão 辞
            return NoteResult(inp.nid, word, FLEXIONADA, message=f"forma flexionada de {res.word}")
        entry, ambiguous = choose_entry(res.entries, _plain(inp.fields.get(nt.F_LEITURA, "")))
        fields, tags = fill.build_fields(conn, res.word, entry, cfg, suru=res.suru)
        changes = fill.merge_fields(inp.fields, fields, overwrite)
        merged = {**inp.fields, **changes}
        merged[nt.F_PALAVRA] = res.word
        jobs = audio.plan_jobs(merged, cfg, existing=inp.fields, overwrite=overwrite)
        new_tags = [t for t in tags if t not in inp.tags]
        status = OK if (changes or jobs or new_tags) else COMPLETA
        return NoteResult(inp.nid, word, status, changes, new_tags, jobs, ambiguous)
    except Exception as e:  # uma nota com problema não derruba as outras
        return NoteResult(inp.nid, word, ERRO, message=f"{type(e).__name__}: {e}")


def process_notes(conn, inputs, cfg, overwrite=False, progress=None, should_cancel=None):
    """Lista de NoteResult, na ordem de `inputs`. `progress(feitas, total)`; `should_cancel()` interrompe."""
    results = []
    for i, inp in enumerate(inputs):
        if should_cancel and should_cancel():
            break
        if progress:
            progress(i, len(inputs))
        results.append(process_note(conn, inp, cfg, overwrite))
    if progress:
        progress(len(results), len(inputs))
    return results


def _list(words, limit=15):
    shown = "、".join(words[:limit])
    return shown + (f" … (+{len(words) - limit})" if len(words) > limit else "")


def summarize(results, total_selected, audio_result=None, cancelled=False):
    """Relatório em texto simples para mostrar ao fim do lote."""
    by = {}
    for r in results:
        by.setdefault(r.status, []).append(r)
    lines = []
    if cancelled:
        lines.append(f"Cancelado: {len(results)} de {total_selected} notas foram processadas.")
    filled = by.get(OK, [])
    lines.append(f"{len(filled)} notas preenchidas ou atualizadas de {total_selected} selecionadas.")
    if by.get(COMPLETA):
        lines.append(f"{len(by[COMPLETA])} já estavam completas.")
    amb = [r.word for r in results if r.ambiguous]
    if amb:
        lines.append(f"\nMais de uma entrada no dicionário (usei a primeira; corrija uma a uma com o botão 辞 ou 再 no editor): "
                     f"{_list(amb)}")
    if by.get(NAO_ACHADA):
        lines.append(f"\nNão encontradas no dicionário: {_list([r.word for r in by[NAO_ACHADA]])}")
    if by.get(FLEXIONADA):
        lines.append("\nForma flexionada (digite a forma de dicionário): " +
                     _list([f"{r.word} ({r.message.replace('forma flexionada de ', '→ ')})" for r in by[FLEXIONADA]]))
    if by.get(VAZIA):
        lines.append(f"\n{len(by[VAZIA])} notas com o campo Palavra vazio.")
    if by.get(ERRO):
        lines.append("\nErros: " + "; ".join(f"{r.word or r.nid}: {r.message}" for r in by[ERRO][:5]))
    if audio_result is not None and audio_result.errors:
        lines.append(f"\n{audio.summarize_errors(audio_result)}")
    return "\n".join(lines)
