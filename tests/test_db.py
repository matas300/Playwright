from src.db import init_db, get_connection


def test_init_db_creates_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    conn = get_connection()
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "posts" in tables
    assert "scan_runs" in tables
    conn.close()


def test_init_db_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    init_db()
