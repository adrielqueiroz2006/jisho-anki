"""Backend de voz: vozes neurais do Edge (ja-JP-NanamiNeural, ja-JP-KeitaNeural).

Serviço não oficial da Microsoft, o mesmo que o pacote edge-tts usa. As constantes e o token
Sec-MS-GEC vêm de uma cópia mínima do edge-tts em vendor/edge_tts (LGPL-3.0); o cliente WebSocket é
nosso (tts/ws.py), porque o Anki não tem aiohttp. Se a Microsoft mudar o protocolo, atualize
vendor/edge_tts com a versão nova do edge-tts.
"""
import json
import os
import secrets
import sys
import time
import uuid
from xml.sax.saxutils import escape

from . import TtsError, ws

_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")
if _VENDOR not in sys.path:
    sys.path.append(_VENDOR)

from edge_tts import constants, drm  # noqa: E402

NAME = "edge"
DEFAULT_VOICE = "ja-JP-NanamiNeural"
VOICES = ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural")
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
MAX_CHUNK_BYTES = 4096


def _date():
    return time.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)", time.gmtime())


def _clean(text):
    # o serviço recusa caracteres de controle
    return "".join(" " if (ord(c) <= 8 or ord(c) in (11, 12) or 14 <= ord(c) <= 31) else c for c in text)


def split_text(text, limit=MAX_CHUNK_BYTES):
    """Quebra `text` (já escapado para XML) em pedaços de no máximo `limit` bytes, preferindo o fim de frase."""
    chunks, current = [], ""
    for part in _sentences(text):
        if len((current + part).encode("utf-8")) > limit and current:
            chunks.append(current)
            current = ""
        while len(part.encode("utf-8")) > limit:  # frase gigante sem pontuação
            cut = len(part) // 2
            while len(part[:cut].encode("utf-8")) > limit:
                cut //= 2
            # não corta no meio de uma entidade XML (&amp;)
            amp = part.rfind("&", 0, cut)
            if amp != -1 and ";" not in part[amp:cut]:
                cut = amp or cut
            chunks.append(part[:cut])
            part = part[cut:]
        current += part
    if current.strip():
        chunks.append(current)
    return chunks


def _sentences(text):
    buf = ""
    for ch in text:
        buf += ch
        if ch in "。！？\n.!?":
            yield buf
            buf = ""
    if buf:
        yield buf


def _ssml(voice, escaped_text):
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        f"<voice name='{voice}'><prosody pitch='+0Hz' rate='+0%' volume='+0%'>{escaped_text}</prosody></voice>"
        "</speak>"
    )


def _headers():
    h = dict(constants.WSS_HEADERS)
    h.pop("Accept-Encoding", None)  # não sabemos decodificar br/zstd
    h["Cookie"] = f"muid={secrets.token_hex(16).upper()};"
    return h


def _url():
    return (f"{constants.WSS_URL}&ConnectionId={uuid.uuid4().hex}"
            f"&Sec-MS-GEC={drm.DRM.generate_sec_ms_gec()}&Sec-MS-GEC-Version={constants.SEC_MS_GEC_VERSION}")


def _connect(timeout):
    try:
        return ws.WebSocket(_url(), _headers(), timeout)
    except ws.HandshakeError as e:
        if e.status != 403:
            raise
        # 403: o relógio do computador está fora; ajusta pelo horário do servidor e tenta uma vez mais
        date = e.headers.get("date")
        parsed = drm.DRM.parse_rfc2616_date(date) if date else None
        if parsed is None:
            raise
        drm.DRM.adj_clock_skew_seconds(parsed - drm.DRM.get_unix_timestamp())
        return ws.WebSocket(_url(), _headers(), timeout)


def _parse_headers(block):
    out = {}
    for line in block.split(b"\r\n"):
        key, _, value = line.partition(b":")
        out[key.strip()] = value.strip()
    return out


def _synth_chunk(escaped, voice, timeout):
    audio = bytearray()
    with _connect(timeout) as sock:
        config = {"context": {"synthesis": {"audio": {
            "metadataoptions": {"sentenceBoundaryEnabled": "false", "wordBoundaryEnabled": "false"},
            "outputFormat": OUTPUT_FORMAT}}}}
        sock.send_text(
            f"X-Timestamp:{_date()}\r\nContent-Type:application/json; charset=utf-8\r\n"
            f"Path:speech.config\r\n\r\n{json.dumps(config, separators=(',', ':'))}\r\n"
        )
        sock.send_text(
            f"X-RequestId:{uuid.uuid4().hex}\r\nContent-Type:application/ssml+xml\r\n"
            f"X-Timestamp:{_date()}Z\r\nPath:ssml\r\n\r\n{_ssml(voice, escaped)}"
        )
        while True:
            op, data = sock.recv()
            if op == ws.OP_TEXT:
                headers = _parse_headers(data.split(b"\r\n\r\n", 1)[0])
                path = headers.get(b"Path")
                if path == b"turn.end":
                    break
                if path not in (b"response", b"turn.start", b"audio.metadata"):
                    raise TtsError(f"resposta desconhecida do serviço de voz: {path!r}")
            elif op == ws.OP_BINARY:
                if len(data) < 2:
                    raise TtsError("mensagem binária sem cabeçalho")
                hl = int.from_bytes(data[:2], "big")
                headers = _parse_headers(data[2:2 + hl])
                if headers.get(b"Path") != b"audio":
                    raise TtsError("mensagem binária que não é áudio")
                payload = data[2 + hl:]
                if payload and headers.get(b"Content-Type") in (b"audio/mpeg", None):
                    audio += payload
            else:  # fechou antes do turn.end
                raise TtsError("o serviço de voz fechou a conexão antes de terminar")
    if not audio:
        raise TtsError("o serviço de voz não devolveu áudio")
    return bytes(audio)


def synthesize(text, voice=DEFAULT_VOICE, timeout=15):
    """MP3 (bytes) com `text` falado por `voice`. Levanta TtsError em qualquer falha."""
    text = text.strip()
    if not text:
        raise TtsError("texto vazio")
    try:
        escaped = escape(_clean(text))
        return b"".join(_synth_chunk(c, voice, timeout) for c in split_text(escaped))
    except TtsError:
        raise
    except Exception as e:
        raise TtsError(f"{type(e).__name__}: {e}") from e
