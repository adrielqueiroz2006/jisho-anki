"""Configuração do addon: config.json + o que o usuário mudou em Ferramentas › Complementos › Config."""
import json
import os

_DEFAULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def defaults():
    with open(_DEFAULTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get():
    """Config atual; fora do Anki devolve os padrões."""
    cfg = defaults()
    try:
        from aqt import mw

        user = mw.addonManager.getConfig(__name__.split(".")[0]) if mw else None
    except ImportError:
        user = None
    if user:
        cfg.update(user)
    return cfg
