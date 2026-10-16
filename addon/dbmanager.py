"""Localização, download e abertura do dicionario.sqlite. Sem dependências do Anki."""
import hashlib
import lzma
import os
import shutil
import urllib.request

from . import lookup

DB_NAME = "dicionario.sqlite"
SCHEMA_VERSION = "1"
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILES = os.path.join(ADDON_DIR, "user_files")  # o Anki preserva esta pasta ao atualizar o addon
# Em modo desenvolvimento a pasta do addon é uma junção; realpath segue o link até a pasta do projeto.
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

_conn = None
_conn_path = None


class DbError(Exception):
    """Banco ausente ou inválido; a mensagem é para o usuário."""


def candidate_paths(cfg):
    paths = []
    if cfg.get("db_path"):
        paths.append(cfg["db_path"])
    paths.append(os.path.join(USER_FILES, DB_NAME))
    # modo desenvolvimento (addon ligado à pasta do projeto): usa o banco gerado por tools/build_db.py
    paths.append(os.path.join(_PROJECT_DIR, "build", DB_NAME))
    return paths


def find_db(cfg):
    for p in candidate_paths(cfg):
        if os.path.isfile(p):
            return p
    return None


def get_connection(cfg):
    """Conexão somente leitura (em cache). Levanta DbError se o banco não existe ou é de outra versão."""
    global _conn, _conn_path
    path = find_db(cfg)
    if path is None:
        raise DbError(
            "O dicionário (dicionario.sqlite) ainda não foi baixado.\n\n"
            "Use Ferramentas › Jisho Card › Baixar dicionário, ou aponte o arquivo em "
            "Ferramentas › Complementos › Jisho Card › Config (campo db_path)."
        )
    if _conn is not None and _conn_path == path:
        return _conn
    close()
    conn = lookup.open_db(path)
    try:
        version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    except Exception as e:
        conn.close()
        raise DbError(f"O arquivo {path} não parece ser um dicionário do Jisho Card ({e}).")
    if not version or version[0] != SCHEMA_VERSION:
        conn.close()
        raise DbError(f"O dicionário em {path} é de outra versão; baixe de novo.")
    _conn, _conn_path = conn, path
    return conn


def install_local_db(src, dest_dir=USER_FILES):
    """Copia um dicionario.sqlite que o usuário já tem para user_files, depois de conferir que é válido."""
    try:
        conn = lookup.open_db(src)
        version = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        conn.close()
    except Exception as e:
        raise DbError(f"Este arquivo não parece ser um dicionário do Jisho Card ({e}).")
    if not version or version[0] != SCHEMA_VERSION:
        raise DbError("Este dicionário é de outra versão do Jisho Card.")
    os.makedirs(dest_dir, exist_ok=True)
    close()
    final = os.path.join(dest_dir, DB_NAME)
    tmp = final + ".part"
    shutil.copyfile(src, tmp)
    os.replace(tmp, final)
    return final


def describe_db(cfg):
    """Resumo do dicionário instalado (caminho, tamanho, versão) para a janela de configurações."""
    path = find_db(cfg)
    if path is None:
        return "Não instalado. Use “Escolher arquivo…” (build/dicionario.sqlite) ou “Baixar”."
    info = [path, f"{os.path.getsize(path) / 1e6:.0f} MB"]
    try:
        conn = lookup.open_db(path)
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        conn.close()
        if meta.get("jmdict_date"):
            info.append(f"JMdict de {meta['jmdict_date']}")
    except Exception:
        info.append("(não consegui ler os metadados)")
    return " · ".join(info)


def close():
    global _conn, _conn_path
    if _conn is not None:
        _conn.close()
    _conn = _conn_path = None


def _fetch(url, dest, progress):
    req = urllib.request.Request(url, headers={"User-Agent": "jisho-card-anki-addon"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)


def download_db(url, progress=None, dest_dir=USER_FILES):
    """Baixa `url` (um .sqlite.xz), confere o SHA-256 de `url + '.sha256'` e instala em user_files.

    `progress(feito, total)` é chamado a cada MB. Devolve o caminho do banco instalado.
    Só substitui o banco antigo depois de tudo conferido.
    """
    if not url:
        raise DbError("Falta o endereço do dicionário (db_url) na configuração do addon.")
    os.makedirs(dest_dir, exist_ok=True)
    xz = os.path.join(dest_dir, DB_NAME + ".xz.part")
    tmp = os.path.join(dest_dir, DB_NAME + ".part")
    try:
        _fetch(url, xz, progress)
        try:
            sha_file = os.path.join(dest_dir, "sha256.part")
            _fetch(url + ".sha256", sha_file, None)
            with open(sha_file) as f:
                expected = f.read().split()[0].lower()
            os.remove(sha_file)
            h = hashlib.sha256()
            with open(xz, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != expected:
                raise DbError("O download veio corrompido (SHA-256 não confere). Tente de novo.")
        except (OSError, ValueError) as e:
            raise DbError(f"Não consegui conferir o arquivo baixado: {e}")
        with lzma.open(xz, "rb") as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        close()
        final = os.path.join(dest_dir, DB_NAME)
        os.replace(tmp, final)
        return final
    except DbError:
        raise
    except Exception as e:
        raise DbError(f"Falha ao baixar o dicionário: {e}")
    finally:
        for p in (xz, tmp):
            if os.path.exists(p):
                os.remove(p)
