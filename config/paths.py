"""Resolve data path settings across dev / editable-install / pipx / future MSI scenarios."""
import os
from pathlib import Path


def resolve_data_path(setting_value: str) -> Path:
    """
    解析顺序：
    1. 绝对路径 → 直接用
    2. 相对路径 + MINEMATE_HOME 已设 → $MINEMATE_HOME / setting_value
    3. 相对路径 + CWD 是项目根（pyproject.toml + minemate/）→ CWD / setting_value
    4. 相对路径 + 源码在工作区内（editable install）→ 沿 __file__.parents 找到项目根
    5. 否则 → ~/.minemate / setting_value
    """
    if not setting_value:
        raise ValueError("setting_value must be non-empty")

    p = Path(setting_value).expanduser()
    if p.is_absolute():
        return p

    home = (os.environ.get("MINEMATE_HOME") or "").strip()
    if home:
        return Path(home).expanduser() / setting_value

    if Path("pyproject.toml").exists() and Path("minemate").is_dir():
        return Path.cwd() / setting_value

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "minemate").is_dir():
            return parent / setting_value

    return Path.home() / ".minemate" / setting_value
