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


def test_collect_env_files_includes_home_minemate(monkeypatch):
    """_collect_env_files should always include ~/.minemate/.env."""
    from pathlib import Path

    from config.settings import _collect_env_files

    monkeypatch.delenv("MINEMATE_HOME", raising=False)
    files = _collect_env_files()
    assert ".env" in files  # CWD
    assert str(Path.home() / ".minemate" / ".env") in files


def test_collect_env_files_with_minemate_home(monkeypatch, tmp_path):
    """When MINEMATE_HOME is set, $MINEMATE_HOME/.env appears before ~/.minemate/.env."""
    from pathlib import Path

    from config.settings import _collect_env_files

    monkeypatch.setenv("MINEMATE_HOME", str(tmp_path))
    files = _collect_env_files()
    custom = f"{tmp_path}/.env"
    home_default = str(Path.home() / ".minemate" / ".env")
    assert custom in files
    assert home_default in files
    # Custom env should come before the home default (higher precedence)
    assert files.index(custom) < files.index(home_default)
