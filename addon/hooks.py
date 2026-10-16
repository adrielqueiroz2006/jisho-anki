"""Ligações com a interface do Anki (só é importado dentro do Anki)."""
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.qt import QAction, QTimer
from aqt.utils import askUser, getFile, showInfo, showWarning, tooltip

from . import audio, browser, dbmanager, editor, notetype, settings, testdeck
from .settings_dialog import SettingsDialog


def _on_profile_open():
    try:
        notetype.ensure_notetype(mw.col)
    except Exception as e:  # nunca travar a abertura do Anki
        showWarning(f"Jisho Card: não consegui criar o note type.\n\n{e}")
    cfg = settings.get()
    if cfg.get("perguntar_download", True) and cfg.get("db_url") and dbmanager.find_db(cfg) is None:
        QTimer.singleShot(800, _offer_download)  # deixa a janela principal terminar de abrir


def _offer_download():
    """Primeira abertura sem dicionário: oferece baixar (uma vez; "Não" desliga a pergunta)."""
    cfg = settings.get()
    if dbmanager.find_db(cfg) is not None:
        return
    if askUser("O Jisho Card precisa do dicionário (cerca de 27 MB, baixado uma vez). Baixar agora?",
               title="Jisho Card (辞書カード)"):
        _download_db()
    else:
        mw.addonManager.writeConfig(__name__.split(".")[0], {**cfg, "perguntar_download": False})
        tooltip("Jisho Card: quando quiser, use Ferramentas › Jisho Card › Baixar dicionário.", period=6000)


def _create_test_deck():
    cfg = settings.get()
    try:
        conn = dbmanager.get_connection(cfg)
        prepared, missing = testdeck.prepare_test_notes(mw.col, conn, cfg)
    except dbmanager.DbError as e:
        showWarning(str(e))
        return
    except Exception as e:
        showWarning(f"Jisho Card: não consegui preparar o deck de teste.\n\n{type(e).__name__}: {e}")
        return
    if not prepared:
        extra = f"\nNão encontradas no dicionário: {', '.join(missing)}" if missing else ""
        showInfo("Jisho Card: o deck de teste já está completo." + extra)
        return
    media_dir = mw.col.media.dir()
    jobs_by_word = {word: audio.plan_jobs(fields, cfg) for word, fields, _tags, _why in prepared}
    all_jobs = [j for jobs in jobs_by_word.values() for j in jobs]

    def progress(done, total):
        label = f"Gerando áudio… {done} de {total}"
        mw.taskman.run_on_main(lambda: mw.progress.update(label=label, value=done, max=total))

    def finish(result):
        try:
            audio_values = {w: audio.apply_result(jobs, result, media_dir, mw.col.media.write_data)
                            for w, jobs in jobs_by_word.items()}
            created = testdeck.commit_test_notes(mw.col, prepared, audio_values)
        except Exception as e:
            showWarning(f"Jisho Card: não consegui criar o deck de teste.\n\n{type(e).__name__}: {e}")
            return
        if hasattr(mw, "reset"):
            mw.reset()
        msg = f"{created} notas novas no deck “{testdeck.DECK_NAME}”."
        if missing:
            msg += f"\nNão encontradas no dicionário: {', '.join(missing)}"
        if result.errors:
            msg += f"\n\n{audio.summarize_errors(result)}"
        showInfo("Jisho Card: " + msg)

    QueryOp(
        parent=mw,
        op=lambda col: audio.run_jobs(all_jobs, cfg, media_dir, progress),
        success=finish,
    ).failure(lambda e: showWarning(f"Jisho Card: {e}")).with_progress("Gerando áudio…").run_in_background()


def _download_db(after=None):
    cfg = settings.get()
    if not cfg["db_url"]:
        showWarning("Jisho Card: o endereço do dicionário (db_url) ainda não está configurado.\n\n"
                    "Em Ferramentas › Complementos › Jisho Card › Config, preencha db_url com o link do "
                    "dicionario.sqlite.xz, ou use Ferramentas › Jisho Card › Escolher arquivo do dicionário.")
        return

    def progress(done, total):
        label = (f"Baixando o dicionário… {done / 1e6:.0f} de {total / 1e6:.0f} MB" if total
                 else f"Baixando o dicionário… {done / 1e6:.0f} MB")
        mw.taskman.run_on_main(lambda: mw.progress.update(label=label, value=done, max=total or 0))

    QueryOp(
        parent=mw,
        op=lambda col: dbmanager.download_db(cfg["db_url"], progress),
        success=lambda path: (tooltip(f"Jisho Card: dicionário instalado em {path}"), after and after()),
    ).failure(lambda e: showWarning(f"Jisho Card: {e}")).with_progress("Baixando o dicionário…").run_in_background()


def _pick_local_db(after=None):
    def install(path):
        try:
            dest = dbmanager.install_local_db(path)
        except dbmanager.DbError as e:
            showWarning(f"Jisho Card: {e}")
            return
        tooltip(f"Jisho Card: dicionário instalado em {dest}")
        if after:
            after()

    getFile(mw, "Escolha o arquivo dicionario.sqlite", install, filter="Dicionário (*.sqlite)", key="jisho_db")


def _open_settings():
    """Janela de configurações; grava com addonManager.writeConfig. Devolve True se o usuário salvou."""
    pkg = __name__.split(".")[0]

    def refresh():
        dlg.set_db_status(dbmanager.describe_db({**settings.get(), "db_path": dlg.db_path.text().strip()}))

    def download():
        # usa o endereço digitado agora, mesmo antes de salvar
        mw.addonManager.writeConfig(pkg, {**settings.get(), "db_url": dlg.db_url.text().strip()})
        _download_db(after=refresh)

    dlg = SettingsDialog(mw, settings.get(), dbmanager.describe_db(settings.get()),
                         on_pick_db=lambda: _pick_local_db(after=refresh), on_download_db=download)
    if dlg.exec():
        mw.addonManager.writeConfig(pkg, dlg.values())
        dbmanager.close()  # db_path pode ter mudado
        tooltip("Jisho Card: configurações salvas.")
        return True
    return False


def setup():
    gui_hooks.profile_did_open.append(_on_profile_open)
    editor.setup()
    browser.setup()
    mw.addonManager.setConfigAction(__name__.split(".")[0], _open_settings)
    menu = mw.form.menuTools.addMenu("Jisho Card (辞書カード)")
    for text, fn in (("Configurações…", _open_settings),
                     ("Escolher arquivo do dicionário…", _pick_local_db),
                     ("Baixar dicionário", _download_db),
                     ("Criar deck de teste (20 palavras)", _create_test_deck)):
        action = QAction(text, mw)
        action.triggered.connect(lambda _checked=False, f=fn: f())
        menu.addAction(action)
