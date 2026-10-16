"""Jisho Card (辞書カード): addon do Anki que preenche cartões de japonês a partir de um dicionário offline."""

try:
    from aqt import mw
except ImportError:  # fora do Anki (testes, scripts de tools/)
    mw = None

if mw is not None:
    from . import hooks

    hooks.setup()
