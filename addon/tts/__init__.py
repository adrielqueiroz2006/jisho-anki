"""Síntese de voz com backends plugáveis (edge, gtts), tentados em ordem.

`synthesize` devolve (mp3_bytes, nome_do_backend). Não depende do Anki; as chamadas de rede ficam
aqui para poderem rodar em segundo plano.
"""


class TtsError(Exception):
    """Falha de síntese; a mensagem é para o usuário/log."""


def _backend(name):
    if name == "edge":
        from . import edge as backend
    elif name == "gtts":
        from . import gtts as backend
    else:
        raise TtsError(f"backend de voz desconhecido: {name}")
    return backend


def synthesize(text, cfg):
    """Tenta cada backend de `cfg["tts_backends"]` até um funcionar. Levanta TtsError com o motivo de cada falha."""
    errors = []
    for name in cfg.get("tts_backends", ["edge", "gtts"]):
        try:
            backend = _backend(name)
            if name == "edge":
                data = backend.synthesize(text, cfg.get("tts_voice", backend.DEFAULT_VOICE))
            else:
                data = backend.synthesize(text)
        except TtsError as e:
            errors.append(f"{name}: {e}")
            continue
        except Exception as e:  # biblioteca ausente, erro inesperado
            errors.append(f"{name}: {type(e).__name__}: {e}")
            continue
        if not looks_like_mp3(data):
            errors.append(f"{name}: o áudio recebido não é MP3")
            continue
        return data, name
    raise TtsError("; ".join(errors) or "nenhum backend de voz configurado")


def looks_like_mp3(data):
    """MP3 começa com uma tag ID3 ou com o sinal de sincronismo de quadro (0xFFEx/0xFFFx)."""
    return len(data) > 128 and (data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0))
