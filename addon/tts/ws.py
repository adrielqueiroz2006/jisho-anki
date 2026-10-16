"""Cliente WebSocket mínimo (RFC 6455) só com a biblioteca padrão.

O Anki não traz aiohttp nem websockets, e o serviço de voz do Edge só fala WebSocket. Cobre o que
precisamos: handshake com cabeçalhos próprios, enviar texto, receber texto/binário (com fragmentos),
responder ping e fechar. Sem compressão (permessage-deflate) e sem proxy.
"""
import base64
import os
import socket
import ssl
import struct
import urllib.parse

OP_CONT, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA


class WebSocketError(Exception):
    pass


class HandshakeError(WebSocketError):
    """O servidor não aceitou a conexão; `status` e `headers` ajudam a decidir se vale tentar de novo."""

    def __init__(self, status, headers, message):
        super().__init__(message)
        self.status = status
        self.headers = headers


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class WebSocket:
    def __init__(self, url, headers=None, timeout=15):
        self._timeout = timeout
        u = urllib.parse.urlsplit(url)
        if u.scheme not in ("wss", "ws"):
            raise WebSocketError(f"esquema não suportado: {u.scheme}")
        port = u.port or (443 if u.scheme == "wss" else 80)
        sock = socket.create_connection((u.hostname, port), timeout=timeout)
        if u.scheme == "wss":
            sock = _ssl_context().wrap_socket(sock, server_hostname=u.hostname)
        self._sock = sock
        self._buf = b""
        self._handshake(u, headers or {})

    # ----- handshake -----
    def _handshake(self, u, headers):
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path + ("?" + u.query if u.query else "")
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {u.hostname}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
        ]
        lines += [f"{k}: {v}" for k, v in headers.items()]
        self._sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise WebSocketError("conexão fechada durante o handshake")
            raw += chunk
        head, _, rest = raw.partition(b"\r\n\r\n")
        self._buf = rest
        status_line, *header_lines = head.decode("latin-1").split("\r\n")
        status = int(status_line.split()[1])
        resp = {}
        for line in header_lines:
            k, _, v = line.partition(":")
            resp[k.strip().lower()] = v.strip()
        if status != 101:
            raise HandshakeError(status, resp, f"o servidor respondeu HTTP {status}")

    # ----- leitura -----
    def _read(self, n):
        while len(self._buf) < n:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise WebSocketError("conexão fechada pelo servidor")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _frame(self):
        b1, b2 = self._read(2)
        fin, opcode = bool(b1 & 0x80), b1 & 0x0F
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._read(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._read(8))[0]
        mask = self._read(4) if b2 & 0x80 else None
        payload = self._read(length)
        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return fin, opcode, payload

    def recv(self):
        """Próxima mensagem completa: (opcode, bytes), com opcode OP_TEXT, OP_BINARY ou OP_CLOSE."""
        message, first_op = b"", None
        while True:
            fin, opcode, payload = self._frame()
            if opcode == OP_PING:
                self._send(OP_PONG, payload)
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_CLOSE:
                return OP_CLOSE, payload
            if opcode != OP_CONT:
                first_op = opcode
            message += payload
            if fin:
                return first_op, message

    # ----- escrita -----
    def _send(self, opcode, payload):
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(header + mask + masked)

    def send_text(self, text):
        self._send(OP_TEXT, text.encode("utf-8"))

    def close(self):
        try:
            self._send(OP_CLOSE, struct.pack(">H", 1000))
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
