"""Integração com o editor de notas: botões 辞 e 再, Ctrl+Shift+J e preenchimento ao sair do campo Palavra.

Funciona no editor padrão do Anki. O editor experimental em SvelteKit (ExperimentFlag.SVELTE_EDITOR)
não expõe `editor.note`; nele o addon só avisa.
"""
import weakref

from anki.utils import strip_html
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.qt import QDialog, QDialogButtonBox, QLabel, QListWidget, QTimer, QVBoxLayout
from aqt.utils import askUser, showWarning, tooltip

from . import audio, dbmanager, fill, settings
from . import notetype as nt

_editors = weakref.WeakSet()
_last_auto = {}  # id(note) -> palavra que já foi preenchida automaticamente


class ChooseEntryDialog(QDialog):
    """Lista as entradas do dicionário para uma palavra com mais de uma acepção (生, 水, 上手...)."""

    def __init__(self, parent, word, entries):
        super().__init__(parent)
        self.setWindowTitle(f"Jisho Card — escolha a entrada de “{word}”")
        self.resize(760, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"“{word}” tem {len(entries)} entradas no dicionário (★ = palavra comum):"))
        self.list = QListWidget()
        for e in entries:
            self.list.addItem(fill.entry_label(e))
        self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        layout.addWidget(self.list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose(self):
        return self.list.currentRow() if self.exec() else None


def _is_jisho(note):
    return note is not None and note.note_type()["name"] == nt.NOTETYPE_NAME


def _word(note):
    return strip_html(note[nt.F_PALAVRA]).replace("\xa0", " ").strip()


def _reload(editor):
    if hasattr(editor, "loadNoteKeepingFocus"):
        editor.loadNoteKeepingFocus()
    else:
        editor.loadNote()


def fill_editor(editor, overwrite=False, auto=False):
    """Preenche a nota aberta no editor. `overwrite=True` é o "Regerar"."""
    note = getattr(editor, "note", None)
    if note is None:
        if not auto:
            showWarning("Jisho Card: o editor experimental (SvelteKit) ainda não é suportado. "
                        "Desligue-o em Ferramentas › Preferências › Experimentos.")
        return
    if not _is_jisho(note):
        if not auto:
            tooltip(f"Jisho Card: escolha o tipo de nota “{nt.NOTETYPE_NAME}”.", parent=editor.widget)
        return
    if auto:
        _fill_saved(editor, overwrite, auto)
    else:
        editor.call_after_note_saved(lambda: _fill_saved(editor, overwrite, auto), keepFocus=True)


def _fill_saved(editor, overwrite, auto):
    note = editor.note
    word = _word(note)
    if not word:
        if not auto:
            tooltip("Jisho Card: digite a palavra no primeiro campo.", parent=editor.widget)
        return
    cfg = settings.get()
    try:
        conn = dbmanager.get_connection(cfg)
    except dbmanager.DbError as e:
        if auto:
            tooltip(str(e).split("\n")[0], parent=editor.widget)
        else:
            showWarning(str(e))
        return
    try:
        res = fill.resolve_word(conn, word)
        if not res.entries:
            tooltip(f"Jisho Card: “{word}” não está no dicionário.", parent=editor.widget)
            return
        if res.kind == "base" and not askUser(
                f"“{res.original}” é uma forma flexionada. Usar a forma de dicionário “{res.word}”?",
                parent=editor.widget):
            return
        entry = res.entries[0]
        if fill.needs_choice(res.entries):
            idx = ChooseEntryDialog(editor.widget, res.word, res.entries).choose()
            if idx is None:
                return
            entry = res.entries[idx]
        if overwrite and not askUser(
                "Regerar substitui o conteúdo gerado (leitura, significado, kanji, exemplo...) pelo do dicionário, "
                "inclusive o que você editou. Palavra e Notas ficam como estão. Continuar?", parent=editor.widget):
            return
        fields, tags = fill.build_fields(conn, res.word, entry, cfg, suru=res.suru)
        changes = fill.merge_fields(dict(note.items()), fields, overwrite)
        if res.word != word:
            changes[nt.F_PALAVRA] = res.word
        for name, value in changes.items():
            note[name] = value
        for tag in tags:
            note.add_tag(tag)
        if note.id:
            mw.col.update_note(note)
        _reload(editor)
        tooltip(f"Jisho Card: {len(changes)} campos preenchidos." if changes
                else "Jisho Card: nada a preencher; os campos já têm conteúdo.", parent=editor.widget)
        _generate_audio(editor, note, cfg, overwrite)
    except Exception as e:  # nunca derrubar o editor
        showWarning(f"Jisho Card: erro ao preencher “{word}”.\n\n{type(e).__name__}: {e}")


def _generate_audio(editor, note, cfg, overwrite):
    """Sintetiza o áudio em segundo plano e grava nos campos quando terminar (a nota já está preenchida)."""
    values = dict(note.items())
    jobs = audio.plan_jobs(values, cfg, existing=values, overwrite=overwrite)
    if not jobs:
        return
    media_dir = mw.col.media.dir()
    tooltip("Jisho Card: gerando áudio…", period=1500, parent=editor.widget)

    def done(result):
        written = audio.apply_result(jobs, result, media_dir, mw.col.media.write_data)
        for name, value in written.items():
            if overwrite or fill.is_blank(note[name]):
                note[name] = value
        if written and getattr(editor, "note", None) is note:
            if note.id:
                mw.col.update_note(note)
            _reload(editor)
        msg = audio.summarize_errors(result)
        if msg:
            tooltip("Jisho Card: " + msg, period=5000, parent=editor.widget)

    QueryOp(parent=editor.widget, op=lambda col: audio.run_jobs(jobs, cfg, media_dir),
            success=done).failure(lambda e: tooltip(f"Jisho Card: erro no áudio: {e}", period=5000)).run_in_background()


def _find_editor(note):
    for ed in list(_editors):
        if getattr(ed, "note", None) is note:
            return ed
    return None


def _on_unfocus(changed, note, field_idx):
    """Ao sair do campo Palavra de uma nota nova e vazia, preenche sozinho."""
    try:
        if field_idx != 0 or not settings.get()["auto_preencher"] or not _is_jisho(note):
            return changed
        word = _word(note)
        if not word or _last_auto.get(id(note)) == word:
            return changed
        if not all(fill.is_blank(v) for k, v in note.items() if k != nt.F_PALAVRA):
            return changed
        editor = _find_editor(note)
        if editor is None:
            return changed
        _last_auto[id(note)] = word
        QTimer.singleShot(0, lambda: fill_editor(editor, auto=True))
    except Exception:
        pass
    return changed


def _add_buttons(buttons, editor):
    buttons.append(editor.addButton(
        None, "jisho_fill", lambda ed: fill_editor(ed),
        tip="Preencher com o dicionário (Ctrl+Shift+J)", label="辞", keys="Ctrl+Shift+J"))
    buttons.append(editor.addButton(
        None, "jisho_regen", lambda ed: fill_editor(ed, overwrite=True),
        tip="Regerar: substitui os campos gerados (menos Palavra e Notas)", label="再"))


def setup():
    gui_hooks.editor_did_init.append(_editors.add)
    gui_hooks.editor_did_init_buttons.append(_add_buttons)
    gui_hooks.editor_did_unfocus_field.append(_on_unfocus)
