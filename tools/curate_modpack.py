"""Curate a modpack recommendation based on user requirements.

Combines tag-based recommendation with compatibility checking
to produce an organized mod list suitable for a themed modpack.
"""
from loguru import logger

from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod
from tools.compatibility import check_mod_compatibility_with_session


def curate_modpack(
    themes: list[str],
    mc_version: str | None = None,
    loader: str | None = None,
    preference: str = "",  # "轻量" / "大型" / "硬核" etc
    max_mods: int = 15,
) -> dict:
    """Curate a themed modpack.

    Returns dict with categories and compatibility info.
    """
    try:
        with SessionLocal() as session:
            # 1. Find candidate mods by tags
            candidates = _find_by_tags(session, themes, mc_version, loader, limit=max_mods * 3)
            if not candidates:
                return {"error": "no matching mods found", "mods": [], "compatibility": {}}

            # 2. Filter by preference
            if "轻量" in preference:
                candidates = [m for m in candidates if _is_lightweight(m)]
            elif "大型" in preference or "硬核" in preference:
                candidates = [m for m in candidates if not _is_lightweight(m)]

            # 3. Select top mods
            selected = _select_diverse(candidates, max_mods)

            # 4. Check compatibility among selected
            compat = _check_cross_compatibility(session, selected)

            # 5. Categorize
            categorized = _categorize(selected)

            return {
                "theme": ", ".join(themes),
                "mc_version": mc_version,
                "loader": loader,
                "preference": preference,
                "total_mods": len(selected),
                "categories": categorized,
                "compatibility_notes": compat,
                "disclaimer": "此整合包由 AI 自动推荐，请在实际使用前测试兼容性。",
            }
    except Exception as e:
        logger.exception("curate_modpack failed")
        return {"error": str(e)}


def _find_by_tags(session, themes, mc_version, loader, limit):

    q = session.query(Mod).filter(Mod.tags.isnot(None), Mod.description.isnot(None))
    if loader:
        q = q.filter(Mod.loader.contains(loader))

    rows = q.limit(limit).all()
    scored = []
    for m in rows:
        if not m.tags:
            continue
        if mc_version and mc_version not in (m.mc_versions or []):
            continue
        genres = m.tags.get("genres", [])
        score = sum(1 for t in themes if t in genres)
        if score > 0:
            scored.append((score, m))
    scored.sort(key=lambda x: -x[0])
    return [m for _, m in scored]


def _is_lightweight(mod) -> bool:
    """Heuristic: mods with short descriptions and simple tags are lighter."""
    desc = mod.description or ""
    if len(desc) < 300:
        return True
    tags = mod.tags or {}
    genres = tags.get("genres", [])
    if "辅助" in genres or "优化" in genres or "装饰" in genres:
        return True
    if "科技" in genres and len(desc) > 1000:
        return False
    return len(desc) < 800


def _select_diverse(candidates, max_mods):
    """Select a diverse set covering different genres."""
    selected = []
    seen_genres = set()
    # First pass: pick one from each genre
    for m in candidates:
        genres = set((m.tags or {}).get("genres", []))
        if not (genres & seen_genres):
            selected.append(m)
            seen_genres |= genres
    # Second pass: fill remaining slots by score
    for m in candidates:
        if len(selected) >= max_mods:
            break
        if m not in selected:
            selected.append(m)
    return selected[:max_mods]


def _check_cross_compatibility(session, mods) -> list[str]:
    notes = []
    for i, a in enumerate(mods):
        for b in mods[i + 1 :]:
            result = check_mod_compatibility_with_session(session, a.mod_id, b.mod_id)
            if result.get("known_integration"):
                notes.append(f"{a.name_zh} ↔ {b.name_zh}: {result.get('evidence', '已知联动')}")
            common_ver = result.get("common_mc_versions", [])
            if not common_ver and not result.get("known_integration"):
                notes.append(f"⚠️ {a.name_zh} 和 {b.name_zh} 无共同 MC 版本")
    return notes


def _categorize(mods) -> dict[str, list[dict]]:
    cats: dict[str, list] = {"核心模组": [], "辅助/优化": [], "装饰/建筑": [], "其他": []}
    for m in mods:
        tags = m.tags or {}
        genres = tags.get("genres", [])
        if "辅助" in genres or "优化" in genres:
            cats["辅助/优化"].append(_mod_dict(m))
        elif "装饰" in genres or "建筑" in genres:
            cats["装饰/建筑"].append(_mod_dict(m))
        else:
            cats["核心模组"].append(_mod_dict(m))
    # Move overflow from 核心 to 其他
    if len(cats["核心模组"]) > 8:
        cats["其他"] = cats["核心模组"][8:]
        cats["核心模组"] = cats["核心模组"][:8]
    return {k: v for k, v in cats.items() if v}


def _mod_dict(m) -> dict:
    return {
        "mod_id": m.mod_id,
        "name_zh": m.name_zh,
        "name_en": m.name_en,
        "mcmod_url": m.mcmod_url,
        "loader": m.loader,
        "mc_versions": m.mc_versions or [],
        "tags": m.tags,
        "description": (m.description or "")[:200],
    }
