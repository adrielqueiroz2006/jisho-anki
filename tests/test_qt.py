"""Janelas Qt (configurações e escolha de entrada) rodando offscreen, sem abrir o Anki."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("aqt")

from aqt.qt import QApplication  # noqa: E402

from addon import settings  # noqa: E402
from addon.settings_dialog import SettingsDialog  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_janela_devolve_a_configuracao_atual_sem_mudar_nada(app):
    cfg = settings.defaults()
    assert SettingsDialog(None, cfg).values() == cfg


def test_janela_grava_o_que_o_usuario_mudou(app):
    cfg = settings.defaults()
    d = SettingsDialog(None, cfg)
    d.onyomi.setCurrentIndex(1)
    d.max_acepcoes.setValue(3)
    d.auto.setChecked(False)
    d.audio.setChecked(False)
    d.voice.setCurrentIndex(1)
    d.backends.setCurrentIndex(2)
    d.lote.setChecked(True)
    d.db_url.setText("  https://exemplo/d.sqlite.xz ")
    d.db_path.setText("C:/x/dicionario.sqlite")
    v = d.values()
    assert v["onyomi_script"] == "katakana" and v["max_acepcoes"] == 3
    assert v["auto_preencher"] is False and v["gerar_audio"] is False
    assert v["tts_voice"] == "ja-JP-KeitaNeural" and v["tts_backends"] == ["gtts"]
    assert v["lote_sobrescrever"] is True
    assert v["db_url"] == "https://exemplo/d.sqlite.xz" and v["db_path"] == "C:/x/dicionario.sqlite"


def test_valor_editado_a_mao_no_json_nao_e_trocado_sem_avisar(app):
    cfg = {**settings.defaults(), "tts_voice": "ja-JP-OutraNeural", "tts_backends": ["gtts", "edge"], "chave_extra": 1}
    v = SettingsDialog(None, cfg).values()
    assert v["tts_voice"] == "ja-JP-OutraNeural" and v["tts_backends"] == ["gtts", "edge"] and v["chave_extra"] == 1


def test_botoes_do_dicionario_chamam_as_funcoes(app):
    called = []
    d = SettingsDialog(None, settings.defaults(), "ok", on_pick_db=lambda: called.append("pick"),
                       on_download_db=lambda: called.append("down"))
    d.pick_btn.click()
    d.download_btn.click()
    assert called == ["pick", "down"] and d.db_status.text() == "ok"
    d.set_db_status("novo")
    assert d.db_status.text() == "novo"
    assert not SettingsDialog(None, settings.defaults()).pick_btn.isEnabled()


def test_janela_de_escolha_lista_as_entradas_e_devolve_a_linha(app):
    from addon import dbmanager, editor, fill

    entries = fill.resolve_word(dbmanager.get_connection(settings.defaults()), "生").entries
    d = editor.ChooseEntryDialog(None, "生", entries)
    assert d.list.count() == len(entries) > 1 and d.list.currentRow() == 0
    d.list.setCurrentRow(2)
    assert d.list.currentRow() == 2
    assert "生" in d.windowTitle()


def test_janela_de_configuracoes_como_imagem(app, tmp_path):
    """Só confere que renderiza (e deixa uma captura em build/ para olhar)."""
    from addon import dbmanager

    d = SettingsDialog(None, settings.defaults(), dbmanager.describe_db(settings.defaults()), lambda: None, lambda: None)
    d.resize(640, 480)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "config_dialog.png")
    assert d.grab().save(out)
