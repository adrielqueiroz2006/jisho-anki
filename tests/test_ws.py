"""Cliente WebSocket e protocolo do Edge contra um servidor local de mentira (sem internet)."""
import json
import socket
import struct
import threading

import pytest

from addon.tts import edge, ws


def _frame(opcode, payload, fin=True):
    head = bytes([(0x80 if fin else 0) | opcode])
    n = len(payload)
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack(">H", n)
    else:
        head += bytes([127]) + struct.pack(">Q", n)
    return head + payload


def _read_client_frame(conn):
    def read(n):
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise EOFError
            buf += chunk
        return buf

    b1, b2 = read(2)
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack(">H", read(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read(8))[0]
    assert b2 & 0x80, "o cliente tem que mascarar os quadros"
    mask = read(4)
    data = bytes(b ^ mask[i % 4] for i, b in enumerate(read(length)))
    return b1 & 0x0F, data


class FakeServer:
    """Aceita uma conexão, faz o handshake e roda `script(conn)`."""

    def __init__(self, script, status="101 Switching Protocols", extra_headers=""):
        self.script, self.status, self.extra = script, status, extra_headers
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.request = b""
        self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            conn, _ = self.sock.accept()
            while b"\r\n\r\n" not in self.request:
                self.request += conn.recv(4096)
            conn.sendall(f"HTTP/1.1 {self.status}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                         f"{self.extra}\r\n".encode())
            if self.status.startswith("101"):
                self.script(conn)
            conn.close()
        except Exception as e:  # noqa: BLE001
            self.error = e
        finally:
            self.sock.close()

    @property
    def url(self):
        return f"ws://127.0.0.1:{self.port}/x?a=1"


def test_handshake_envia_cabecalhos_e_recebe_texto_e_binario_fragmentado():
    def script(conn):
        conn.sendall(_frame(ws.OP_TEXT, "olá".encode()))
        conn.sendall(_frame(ws.OP_BINARY, b"aa", fin=False) + _frame(ws.OP_CONT, b"bb"))
        conn.sendall(_frame(ws.OP_BINARY, b"x" * 70000))  # comprimento de 64 bits
        conn.sendall(_frame(ws.OP_CLOSE, b"\x03\xe8"))

    srv = FakeServer(script)
    with ws.WebSocket(srv.url, {"Origin": "chrome-extension://abc", "Cookie": "muid=1;"}) as sock:
        assert sock.recv() == (ws.OP_TEXT, "olá".encode())
        assert sock.recv() == (ws.OP_BINARY, b"aabb")
        op, data = sock.recv()
        assert op == ws.OP_BINARY and data == b"x" * 70000
        assert sock.recv()[0] == ws.OP_CLOSE
    req = srv.request.decode()
    assert req.startswith("GET /x?a=1 HTTP/1.1") and "Upgrade: websocket" in req and "Sec-WebSocket-Key:" in req
    assert "Origin: chrome-extension://abc" in req and "Cookie: muid=1;" in req


def test_ping_e_respondido_e_texto_sai_mascarado():
    got = {}

    def script(conn):
        conn.sendall(_frame(ws.OP_PING, b"oi"))
        got["pong"] = _read_client_frame(conn)
        conn.sendall(_frame(ws.OP_TEXT, b"ok"))
        got["text"] = _read_client_frame(conn)

    srv = FakeServer(script)
    with ws.WebSocket(srv.url) as sock:
        # o ping chega primeiro: recv responde com pong e devolve a mensagem seguinte
        assert sock.recv() == (ws.OP_TEXT, b"ok")
        sock.send_text("x" * 200)  # força o comprimento de 16 bits
    srv.thread.join(2)
    assert got["pong"] == (ws.OP_PONG, b"oi")
    assert got["text"] == (ws.OP_TEXT, b"x" * 200)


def test_handshake_recusado_traz_status_e_cabecalhos():
    srv = FakeServer(lambda c: None, status="403 Forbidden", extra_headers="Date: Wed, 21 Oct 2026 07:28:00 GMT\r\n")
    with pytest.raises(ws.HandshakeError) as e:
        ws.WebSocket(srv.url)
    assert e.value.status == 403 and e.value.headers["date"].startswith("Wed, 21 Oct 2026")


def test_esquema_invalido():
    with pytest.raises(ws.WebSocketError):
        ws.WebSocket("http://x/")


# ---- protocolo do Edge ----

def _edge_server(audio_chunks, hold_end=False):
    seen = []

    def script(conn):
        seen.append(_read_client_frame(conn))   # speech.config
        seen.append(_read_client_frame(conn))   # ssml
        rid = "RID"
        conn.sendall(_frame(ws.OP_TEXT, f"X-RequestId:{rid}\r\nPath:turn.start\r\n\r\n{{}}".encode()))
        conn.sendall(_frame(ws.OP_TEXT, f"X-RequestId:{rid}\r\nPath:response\r\n\r\n{{}}".encode()))
        for chunk in audio_chunks:
            head = f"X-RequestId:{rid}\r\nContent-Type:audio/mpeg\r\nPath:audio\r\n".encode()
            conn.sendall(_frame(ws.OP_BINARY, len(head).to_bytes(2, "big") + head + chunk))
        head = f"X-RequestId:{rid}\r\nPath:audio\r\n".encode()  # fim do fluxo: sem Content-Type e sem dados
        conn.sendall(_frame(ws.OP_BINARY, len(head).to_bytes(2, "big") + head))
        if not hold_end:
            conn.sendall(_frame(ws.OP_TEXT, f"X-RequestId:{rid}\r\nPath:turn.end\r\n\r\n{{}}".encode()))

    return FakeServer(script), seen


@pytest.fixture()
def fake_edge(monkeypatch):
    def install(audio_chunks, **kw):
        srv, seen = _edge_server(audio_chunks, **kw)
        monkeypatch.setattr(edge, "_url", lambda: srv.url)
        return srv, seen

    return install


def test_edge_junta_o_audio_e_manda_config_e_ssml(fake_edge):
    srv, seen = fake_edge([b"\xff\xf3AAAA", b"BBBB"])
    assert edge.synthesize("食べる & 飲む") == b"\xff\xf3AAAABBBB"
    config_msg, ssml_msg = (m[1].decode() for m in seen)
    assert "Path:speech.config" in config_msg and "audio-24khz-48kbitrate-mono-mp3" in config_msg
    body = config_msg.split("\r\n\r\n", 1)[1]
    assert json.loads(body)["context"]["synthesis"]["audio"]["outputFormat"] == "audio-24khz-48kbitrate-mono-mp3"
    assert "Path:ssml" in ssml_msg and "ja-JP-NanamiNeural" in ssml_msg
    assert "食べる &amp; 飲む" in ssml_msg  # XML escapado


def test_edge_usa_a_voz_pedida(fake_edge):
    srv, seen = fake_edge([b"\xff\xf3AAAA"])
    edge.synthesize("たべる", voice="ja-JP-KeitaNeural")
    assert "ja-JP-KeitaNeural" in seen[1][1].decode()


def test_edge_sem_audio_e_erro(fake_edge):
    fake_edge([])
    with pytest.raises(edge.TtsError, match="não devolveu áudio"):
        edge.synthesize("たべる")


def test_edge_conexao_fechada_antes_do_fim_e_erro(fake_edge):
    fake_edge([b"\xff\xf3AAAA"], hold_end=True)
    with pytest.raises(edge.TtsError):
        edge.synthesize("たべる")


def test_edge_texto_vazio():
    with pytest.raises(edge.TtsError, match="vazio"):
        edge.synthesize("   ")


def test_edge_403_corrige_o_relogio_e_tenta_de_novo(monkeypatch):
    from edge_tts import drm

    srv = FakeServer(lambda c: None, status="403 Forbidden", extra_headers="Date: Wed, 21 Oct 2026 07:28:00 GMT\r\n")
    urls = [srv.url]
    good = _edge_server([b"\xff\xf3AAAA"])
    urls.append(good[0].url)
    monkeypatch.setattr(edge, "_url", lambda: urls.pop(0))
    before = drm.DRM.clock_skew_seconds
    try:
        assert edge.synthesize("たべる") == b"\xff\xf3AAAA"
        assert drm.DRM.clock_skew_seconds != before
    finally:
        drm.DRM.clock_skew_seconds = before


def test_split_text_respeita_o_limite_e_o_fim_de_frase():
    text = "あいう。" * 600  # 7200 bytes
    chunks = edge.split_text(text, 4096)
    assert len(chunks) >= 2 and all(len(c.encode()) <= 4096 for c in chunks)
    assert "".join(chunks) == text
    assert all(c.endswith("。") for c in chunks)


def test_split_text_nao_corta_entidade_xml():
    text = "a" * 4090 + "&amp;" + "b" * 100
    chunks = edge.split_text(text, 4096)
    assert "".join(chunks) == text
    assert all("&" not in c or c.count("&") == c.count(";") for c in chunks)


def test_token_sec_ms_gec_tem_o_formato_v2():
    from edge_tts import drm

    token = drm.DRM.generate_sec_ms_gec()
    left, right = token.split("-")
    assert len(left) == 16 and len(right) == 64 and token == token.upper()
