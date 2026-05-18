from pathlib import Path

from config.settings import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    s = Settings(_env_file=None)
    assert s.deepseek_api_key == "sk-test"
    assert s.chunk_size == 512
    assert s.top_k == 8


def test_chroma_collection_default():
    s = Settings(_env_file=None)
    assert s.chroma_collection == "mcmod_v1"


def test_resolved_sqlite_path_returns_pathlib(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    s = Settings(_env_file=None)
    assert isinstance(s.resolved_sqlite_path, Path)


def test_resolved_sqlite_path_respects_absolute(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/custom.db")
    s = Settings(_env_file=None)
    assert str(s.resolved_sqlite_path).replace("\\", "/").endswith("/tmp/custom.db")
