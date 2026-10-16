"""Janela de configurações do Jisho Card (Ferramentas › Jisho Card › Configurações, ou o botão Config do Anki).

Só usa Qt: recebe a configuração atual e devolve a nova em `values()`, sem tocar no Anki.
"""
from aqt.qt import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, Qt, QVBoxLayout,
)

VOICES = [("Nanami (feminina)", "ja-JP-NanamiNeural"), ("Keita (masculina)", "ja-JP-KeitaNeural")]
BACKENDS = [
    ("Edge, com Google de reserva", ["edge", "gtts"]),
    ("Só Edge", ["edge"]),
    ("Só Google (gTTS)", ["gtts"]),
]
SCRIPTS = [("Hiragana (しょく)", "hiragana"), ("Katakana (ショク)", "katakana")]


def _combo(options, current):
    box = QComboBox()
    for label, value in options:
        box.addItem(label, value)
    index = next((i for i in range(box.count()) if box.itemData(i) == current), -1)
    if index == -1:  # valor que o usuário editou à mão no config.json: mantém, em vez de trocar sem avisar
        box.addItem(f"Personalizado ({current})", current)
        index = box.count() - 1
    box.setCurrentIndex(index)
    return box


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, db_status="", on_pick_db=None, on_download_db=None):
        super().__init__(parent)
        self.setWindowTitle("Jisho Card — configurações")
        self.setMinimumWidth(520)
        self._cfg = dict(cfg)

        form = QFormLayout()
        self.onyomi = _combo(SCRIPTS, cfg.get("onyomi_script", "hiragana"))
        form.addRow("Leituras onyomi em", self.onyomi)
        self.max_acepcoes = QSpinBox()
        self.max_acepcoes.setRange(1, 20)
        self.max_acepcoes.setValue(int(cfg.get("max_acepcoes", 6)))
        form.addRow("Máximo de acepções no significado", self.max_acepcoes)
        self.auto = QCheckBox("Preencher ao sair do campo Palavra (em nota nova e vazia)")
        self.auto.setChecked(bool(cfg.get("auto_preencher", True)))
        form.addRow(self.auto)

        self.audio = QCheckBox("Gerar áudio da palavra e da frase (usa a internet)")
        self.audio.setChecked(bool(cfg.get("gerar_audio", True)))
        form.addRow(self.audio)
        self.voice = _combo(VOICES, cfg.get("tts_voice", "ja-JP-NanamiNeural"))
        form.addRow("Voz", self.voice)
        self.backends = _combo([(label, tuple(v)) for label, v in BACKENDS], tuple(cfg.get("tts_backends", ["edge", "gtts"])))
        form.addRow("Serviço de voz", self.backends)

        self.lote = QCheckBox("No lote, substituir campos já preenchidos (o menu “Regerar” sempre substitui)")
        self.lote.setChecked(bool(cfg.get("lote_sobrescrever", False)))
        form.addRow(self.lote)

        self.db_status = QLabel(db_status or "Dicionário não instalado.")
        self.db_status.setWordWrap(True)
        self.db_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Dicionário", self.db_status)
        buttons_db = QHBoxLayout()
        self.pick_btn = QPushButton("Escolher arquivo…")
        self.download_btn = QPushButton("Baixar")
        for btn, fn in ((self.pick_btn, on_pick_db), (self.download_btn, on_download_db)):
            btn.setEnabled(fn is not None)
            if fn:
                btn.clicked.connect(fn)
            buttons_db.addWidget(btn)
        buttons_db.addStretch()
        form.addRow("", buttons_db)
        self.ask_download = QCheckBox("Oferecer baixar o dicionário ao abrir o Anki, se ele não estiver instalado")
        self.ask_download.setChecked(bool(cfg.get("perguntar_download", True)))
        form.addRow(self.ask_download)
        self.db_url = QLineEdit(cfg.get("db_url", ""))
        self.db_url.setPlaceholderText("link do dicionario.sqlite.xz (release do GitHub)")
        form.addRow("Endereço para baixar", self.db_url)
        self.db_path = QLineEdit(cfg.get("db_path", ""))
        self.db_path.setPlaceholderText("opcional: caminho de um dicionario.sqlite já existente")
        form.addRow("Arquivo local", self.db_path)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def set_db_status(self, text):
        self.db_status.setText(text)

    def values(self):
        """A configuração com o que está na janela (chaves que a janela não mostra ficam como vieram)."""
        cfg = dict(self._cfg)
        cfg.update({
            "onyomi_script": self.onyomi.currentData(),
            "max_acepcoes": self.max_acepcoes.value(),
            "auto_preencher": self.auto.isChecked(),
            "gerar_audio": self.audio.isChecked(),
            "tts_voice": self.voice.currentData(),
            "tts_backends": list(self.backends.currentData()),
            "lote_sobrescrever": self.lote.isChecked(),
            "perguntar_download": self.ask_download.isChecked(),
            "db_url": self.db_url.text().strip(),
            "db_path": self.db_path.text().strip(),
        })
        return cfg
