"""Backend de reserva: Google Tradutor (biblioteca gTTS, em vendor/). Só precisa de `requests`, que o Anki traz."""
import io
import os
import sys

from . import TtsError

_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")
if _VENDOR not in sys.path:
    sys.path.append(_VENDOR)

NAME = "gtts"


def synthesize(text, lang="ja"):
    text = text.strip()
    if not text:
        raise TtsError("texto vazio")
    from gtts import gTTS  # importado aqui para o addon abrir mesmo se a biblioteca falhar

    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except Exception as e:
        raise TtsError(f"{type(e).__name__}: {e}") from e
    return buf.getvalue()
