"""Preenchimento em lote no navegador de cards: menu "Jisho Card" e item no menu de contexto."""
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.operations.note import update_notes
from aqt.qt import QAction
from aqt.utils import askUser, showText, showWarning, tooltip

from . import audio, batch, dbmanager, fill, settings
from . import notetype as nt

WORKERS = 3          # sínteses de voz em paralelo
CONFIRM_ABOVE = 40   # a partir daqui avisa que vai demorar


def _jisho_notes(browser):
    notes = []
    for nid in browser.selected_notes():
        note = mw.col.get_note(nid)
        if note.note_type()["name"] == nt.NOTETYPE_NAME:
            notes.append(note)
    return notes


def fill_selected(browser, overwrite=False):
    """Preenche as notas Jisho Card selecionadas. `overwrite=True` regera (substitui o conteúdo gerado)."""
    notes = _jisho_notes(browser)
    if not notes:
        tooltip(f"Jisho Card: selecione notas do tipo “{nt.NOTETYPE_NAME}”.", parent=browser)
        return
    cfg = settings.get()
    try:
        conn = dbmanager.get_connection(cfg)
    except dbmanager.DbError as e:
        showWarning(str(e), parent=browser)
        return
    if overwrite and not askUser(
            f"Regerar {len(notes)} notas substitui o conteúdo gerado (leitura, significado, kanji, exemplo, áudio...) "
            "pelo do dicionário, inclusive o que você editou. Palavra e Notas ficam como estão. Continuar?",
            parent=browser):
        return
    if cfg.get("gerar_audio", True) and len(notes) > CONFIRM_ABOVE and not askUser(
            f"{len(notes)} notas com áudio podem levar vários minutos (e usam a internet). "
            "Dá para cancelar com Esc. Continuar?", parent=browser):
        return

    inputs = [batch.NoteInput(n.id, dict(n.items()), list(n.tags)) for n in notes]
    media_dir = mw.col.media.dir()

    def show_progress(label, done, total):
        mw.taskman.run_on_main(lambda: mw.progress.update(label=label, value=done, max=total or 0))

    def op(col):
        results = batch.process_notes(
            conn, inputs, cfg, overwrite,
            progress=lambda d, t: show_progress(f"Lendo o dicionário… {d} de {t}", d, t),
            should_cancel=mw.progress.want_cancel)
        jobs = [j for r in results for j in r.jobs]
        result = audio.run_jobs(
            jobs, cfg, media_dir,
            progress=lambda d, t: show_progress(f"Gerando áudio… {d} de {t}", d, t),
            workers=WORKERS, should_cancel=mw.progress.want_cancel)
        return results, result

    def success(outcome):
        results, audio_result = outcome
        changed = []
        for r in results:
            if r.status != batch.OK:
                continue
            note = mw.col.get_note(r.nid)
            for name, value in r.changes.items():
                note[name] = value
            audio_values = audio.apply_result(r.jobs, audio_result, media_dir, mw.col.media.write_data)
            for name, value in audio_values.items():
                if overwrite or fill.is_blank(note[name]):
                    note[name] = value
            for tag in r.new_tags:
                note.add_tag(tag)
            changed.append(note)
        cancelled = len(results) < len(inputs) or audio_result.cancelled
        report = batch.summarize(results, len(inputs), audio_result, cancelled)
        if changed:
            update_notes(parent=browser, notes=changed).success(
                lambda _c: showText(report, parent=browser, title="Jisho Card — resultado do lote")
            ).run_in_background()
        else:
            showText(report, parent=browser, title="Jisho Card — resultado do lote")

    QueryOp(parent=browser, op=op, success=success).failure(
        lambda e: showWarning(f"Jisho Card: erro no preenchimento em lote.\n\n{type(e).__name__}: {e}",
                              parent=browser)
    ).with_progress("Preenchendo notas…").run_in_background()


def _normal(browser):
    fill_selected(browser, overwrite=bool(settings.get().get("lote_sobrescrever", False)))


def _regen(browser):
    fill_selected(browser, overwrite=True)


def _on_menus(browser):
    menu = browser.menuBar().addMenu("Jisho Card")
    a = QAction("Preencher notas selecionadas", browser)
    a.triggered.connect(lambda: _normal(browser))
    menu.addAction(a)
    b = QAction("Regerar notas selecionadas…", browser)
    b.triggered.connect(lambda: _regen(browser))
    menu.addAction(b)


def _on_context_menu(browser, menu):
    menu.addSeparator()
    a = menu.addAction("Jisho Card: preencher notas selecionadas")
    a.triggered.connect(lambda: _normal(browser))


def setup():
    gui_hooks.browser_menus_did_init.append(_on_menus)
    gui_hooks.browser_will_show_context_menu.append(_on_context_menu)
