from config.settings import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DB", "db")
    s = Settings(_env_file=None)
    assert s.deepseek_api_key == "sk-test"
    assert s.mysql_host == "127.0.0.1"
    assert s.chunk_size == 512
    assert s.top_k == 8


def test_mysql_url(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("MYSQL_HOST", "h")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "u")
    monkeypatch.setenv("MYSQL_PASSWORD", "p")
    monkeypatch.setenv("MYSQL_DB", "d")
    s = Settings(_env_file=None)
    assert "mysql+pymysql://u:p@h:3306/d" in s.mysql_url
