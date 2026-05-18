"""Test resolve_data_path fallback levels."""
from pathlib import Path

import pytest

from config.paths import resolve_data_path


def test_absolute_path_returns_unchanged(tmp_path):
    """Level 1: absolute paths returned as-is."""
    abs_p = tmp_path / "foo.db"
    result = resolve_data_path(str(abs_p))
    assert result == abs_p


def test_minemate_home_env_takes_precedence(monkeypatch, tmp_path):
    """Level 2: MINEMATE_HOME env var → $MINEMATE_HOME / setting_value."""
    monkeypatch.setenv("MINEMATE_HOME", str(tmp_path))
    result = resolve_data_path("foo.db")
    assert result == tmp_path / "foo.db"


def test_cwd_project_root_match(monkeypatch, tmp_path):
    """Level 3: CWD with pyproject.toml + minemate/ → CWD / value."""
    monkeypatch.delenv("MINEMATE_HOME", raising=False)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "minemate").mkdir()
    monkeypatch.chdir(tmp_path)
    result = resolve_data_path("foo.db")
    assert result == tmp_path / "foo.db"


def test_fallback_no_double_path_component(monkeypatch, tmp_path):
    """Level 5: fallback should produce single-layer path (no fallback_subdir duplication)."""
    monkeypatch.delenv("MINEMATE_HOME", raising=False)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    result = resolve_data_path("foo.db")
    parts_str = str(result)
    assert parts_str.count("foo.db") == 1, f"Path has duplicate foo.db: {parts_str}"


def test_empty_setting_raises():
    """Empty string setting raises ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        resolve_data_path("")


def test_chroma_path_default_no_double_layer(monkeypatch, tmp_path):
    """The Phase 1 bug: chroma_path='chroma' should NOT yield .../chroma/chroma."""
    monkeypatch.setenv("MINEMATE_HOME", str(tmp_path))
    result = resolve_data_path("chroma")
    assert result == tmp_path / "chroma"
    # Ensure no adjacent 'chroma/chroma' duplication (the Phase 1 bug)
    assert "chroma/chroma" not in result.as_posix()
