from click.testing import CliRunner

from minemate.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "setup" in result.output
    assert "start" in result.output
    assert "status" in result.output


def test_status_fails_without_env():
    """Without DEEPSEEK_API_KEY set, status should still run (it catches exceptions)."""
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    # Status handles missing env gracefully
    assert result.exit_code == 0
    assert "MineMate Status" in result.output


def _make_test_zip(tmp_path, mod_count=1):
    """Helper: build a tiny valid minemate-data zip for tests."""
    import json
    import sqlite3
    import zipfile

    db_src = tmp_path / "src.db"
    conn = sqlite3.connect(db_src)
    conn.execute("CREATE TABLE mods (mod_id TEXT PRIMARY KEY)")
    for i in range(mod_count):
        conn.execute("INSERT INTO mods VALUES (?)", (f"mod_{i}",))
    conn.commit()
    conn.close()

    zip_path = tmp_path / "data.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({
            "mod_count": mod_count,
            "sqlite_filename": "minemate.db",
            "chroma_subdir": "chroma",
        }))
        zf.write(db_src, "minemate.db")
    return zip_path


def test_import_data_aborts_when_destination_exists(tmp_path):
    """Without force, import_data raises ImportError_ on existing destination."""
    import pytest

    from scripts.import_data import ImportError_, import_data

    zip_path = _make_test_zip(tmp_path)
    dest_db = tmp_path / "minemate.db"
    dest_db.write_text("existing-content")
    dest_chroma = tmp_path / "chroma"
    dest_chroma.mkdir()

    with pytest.raises(ImportError_, match="already present"):
        import_data(zip_path, dest_db, dest_chroma, force=False, echo=lambda *a: None)

    # Original file should be untouched
    assert dest_db.read_text() == "existing-content"


def test_import_data_with_force_overwrites(tmp_path):
    """With force=True, import_data overwrites existing destination."""
    from scripts.import_data import import_data

    zip_path = _make_test_zip(tmp_path, mod_count=3)
    dest_db = tmp_path / "minemate.db"
    dest_db.write_text("OLD")  # placeholder, not a real db
    dest_chroma = tmp_path / "chroma"
    dest_chroma.mkdir()

    manifest = import_data(
        zip_path, dest_db, dest_chroma, force=True, echo=lambda *a: None
    )
    assert manifest["mod_count"] == 3
    # Verify dest_db is now a real SQLite file (header check)
    assert dest_db.read_bytes()[:16] == b"SQLite format 3\x00"


def test_import_data_rejects_corrupted_zip(tmp_path):
    """Bad zip → ImportError_ with 'corrupted' in message."""
    import pytest

    from scripts.import_data import ImportError_, import_data

    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_text("not a zip file")
    dest_db = tmp_path / "minemate.db"
    dest_chroma = tmp_path / "chroma"

    with pytest.raises(ImportError_, match="corrupted"):
        import_data(bad_zip, dest_db, dest_chroma, force=False, echo=lambda *a: None)


def test_build_tags_shows_warning(monkeypatch):
    """build-tags with --yes should skip countdown and call pipeline.tag_mods.main."""
    import sys

    from click.testing import CliRunner

    fake_main_calls = []

    def fake_main():
        fake_main_calls.append(list(sys.argv))

    monkeypatch.setattr("pipeline.tag_mods.main", fake_main)

    runner = CliRunner()
    result = runner.invoke(main, ["build-tags", "--yes", "--workers", "5"])
    assert result.exit_code == 0
    # --yes should skip the warning
    assert "WARNING" not in result.output
    assert len(fake_main_calls) == 1
    assert "--workers" in fake_main_calls[0]
    assert "5" in fake_main_calls[0]


def test_build_index_passes_mod_arg(monkeypatch):
    """build-index --mod X should forward to pipeline.build_index.main with --mod X."""
    import sys

    captured_argv = []

    def fake_main():
        captured_argv.append(list(sys.argv))

    monkeypatch.setattr("pipeline.build_index.main", fake_main)

    from click.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(main, ["build-index", "--mod", "341"])
    assert result.exit_code == 0
    assert captured_argv == [["build_index", "--mod", "341"]]


def test_setup_reports_4_stages(monkeypatch):
    """setup should print install mode + 4 numbered checks and exit 0."""
    from click.testing import CliRunner
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-with-enough-length")

    runner = CliRunner()
    # Provide stdin in case the interactive prompt triggers (shouldn't, since env is set)
    result = runner.invoke(main, ["setup"], input="\n")
    assert result.exit_code == 0
    assert "MineMate Setup Wizard" in result.output
    assert "安装模式:" in result.output
    assert "[1/4]" in result.output
    assert "[2/4]" in result.output
    assert "[3/4]" in result.output
    assert "[4/4]" in result.output


def test_install_chromium_invokes_playwright(monkeypatch):
    """install-chromium should call playwright.__main__.main with ['install', 'chromium']."""
    import sys

    from click.testing import CliRunner

    captured_argv = []

    def fake_pw_main():
        captured_argv.append(list(sys.argv))

    monkeypatch.setattr("playwright.__main__.main", fake_pw_main)

    runner = CliRunner()
    result = runner.invoke(main, ["install-chromium"])
    assert result.exit_code == 0
    assert "Chromium 安装完成" in result.output
    assert captured_argv == [["playwright", "install", "chromium"]]


def test_write_env_var_idempotent(tmp_path):
    """_write_env_var should overwrite existing line, not append duplicate."""
    from minemate.cli import _write_env_var

    env_file = tmp_path / ".env"
    env_file.write_text("FOO=1\nBAR=2\n", encoding="utf-8")

    _write_env_var(env_file, "FOO", "999")
    content = env_file.read_text(encoding="utf-8")
    assert "FOO=999" in content
    assert "FOO=1" not in content
    assert "BAR=2" in content

    _write_env_var(env_file, "NEW", "added")
    content = env_file.read_text(encoding="utf-8")
    assert "NEW=added" in content
    assert "FOO=999" in content


def test_setup_interactive_writes_api_key(monkeypatch, tmp_path):
    """When API key missing, setup should prompt and write to ~/.minemate/.env."""
    from click.testing import CliRunner

    # Make HOME point to tmp_path so writes don't affect real home
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Force API key to be missing: set the pydantic field on the instance to sentinel
    from config.settings import settings as _settings
    monkeypatch.setattr(_settings, "deepseek_api_key", "sk-xxx")

    runner = CliRunner()
    # Provide: confirm "Y\n" (default), then paste fake key "sk-validkey1234567890\n"
    result = runner.invoke(main, ["setup"], input="\nsk-validkey1234567890\n")
    assert result.exit_code == 0
    expected_env = tmp_path / ".minemate" / ".env"
    assert expected_env.exists(), f"Expected env file at {expected_env}"
    content = expected_env.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=sk-validkey1234567890" in content
