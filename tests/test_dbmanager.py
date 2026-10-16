import hashlib
import lzma
import os
import sqlite3

import pytest

from addon import dbmanager


def _make_db(path, version="1"):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    c.execute("INSERT INTO meta VALUES ('schema_version', ?)", (version,))
    c.commit()
    c.close()


def _release(tmp_path, version="1", bad_sha=False):
    db = tmp_path / "src.sqlite"
    _make_db(str(db), version)
    xz = tmp_path / "dicionario.sqlite.xz"
    with open(db, "rb") as f, lzma.open(xz, "wb") as g:
        g.write(f.read())
    digest = "0" * 64 if bad_sha else hashlib.sha256(xz.read_bytes()).hexdigest()
    (tmp_path / "dicionario.sqlite.xz.sha256").write_text(f"{digest}  dicionario.sqlite.xz\n")
    return xz.as_uri()


@pytest.fixture(autouse=True)
def _limpa():
    yield
    dbmanager.close()


def test_baixa_confere_e_instala(tmp_path):
    url = _release(tmp_path)
    dest = tmp_path / "user_files"
    calls = []
    path = dbmanager.download_db(url, progress=lambda d, t: calls.append(d), dest_dir=str(dest))
    assert os.path.basename(path) == "dicionario.sqlite" and os.path.getsize(path) > 0
    assert sorted(os.listdir(dest)) == ["dicionario.sqlite"]  # sem sobras (.part)
    assert calls


def test_sha256_errado_nao_instala(tmp_path):
    url = _release(tmp_path, bad_sha=True)
    dest = tmp_path / "user_files"
    with pytest.raises(dbmanager.DbError, match="SHA-256"):
        dbmanager.download_db(url, dest_dir=str(dest))
    assert os.listdir(dest) == []


def test_sha256_ausente_nao_instala(tmp_path):
    url = _release(tmp_path)
    (tmp_path / "dicionario.sqlite.xz.sha256").unlink()
    with pytest.raises(dbmanager.DbError):
        dbmanager.download_db(url, dest_dir=str(tmp_path / "u"))


def test_url_vazia():
    with pytest.raises(dbmanager.DbError, match="db_url"):
        dbmanager.download_db("")


def test_falha_de_rede_vira_mensagem(tmp_path):
    with pytest.raises(dbmanager.DbError):
        dbmanager.download_db((tmp_path / "nao_existe.xz").as_uri(), dest_dir=str(tmp_path / "u"))


def test_db_path_da_config_tem_prioridade(tmp_path):
    p = tmp_path / "meu.sqlite"
    _make_db(str(p))
    assert dbmanager.find_db({"db_path": str(p)}) == str(p)
    assert dbmanager.get_connection({"db_path": str(p)}) is not None


def test_versao_de_esquema_errada(tmp_path):
    p = tmp_path / "velho.sqlite"
    _make_db(str(p), version="0")
    with pytest.raises(dbmanager.DbError, match="outra versão"):
        dbmanager.get_connection({"db_path": str(p)})


def test_arquivo_que_nao_e_o_dicionario(tmp_path):
    p = tmp_path / "x.sqlite"
    sqlite3.connect(str(p)).close()
    with pytest.raises(dbmanager.DbError):
        dbmanager.get_connection({"db_path": str(p)})


def test_instala_dicionario_local(tmp_path):
    src = tmp_path / "meu.sqlite"
    _make_db(str(src))
    path = dbmanager.install_local_db(str(src), dest_dir=str(tmp_path / "user_files"))
    assert os.path.basename(path) == "dicionario.sqlite" and os.listdir(tmp_path / "user_files") == ["dicionario.sqlite"]


def test_instala_dicionario_local_invalido(tmp_path):
    src = tmp_path / "x.sqlite"
    sqlite3.connect(str(src)).close()
    with pytest.raises(dbmanager.DbError):
        dbmanager.install_local_db(str(src), dest_dir=str(tmp_path / "u"))


def test_modo_dev_acha_o_banco_do_projeto_por_uma_juncao(tmp_path):
    """install_dev.py liga addons21/jisho_card à pasta addon/ por junção; o banco fica em <projeto>/build."""
    import subprocess
    import sys

    from conftest import ROOT

    link = tmp_path / "jisho_card"
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), os.path.join(ROOT, "addon")], capture_output=True)
    if r.returncode != 0:
        pytest.skip("mklink /J indisponível")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import jisho_card.dbmanager as d; "
            "print(d.candidate_paths({})[-1])")
    out = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True)
    os.rmdir(link)
    assert os.path.normcase(out.stdout.strip()) == os.path.normcase(os.path.join(ROOT, "build", "dicionario.sqlite")), out.stderr
