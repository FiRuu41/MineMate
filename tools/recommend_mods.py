"""Mod recommendation by tag matching. Works with both SQLite and MySQL."""
from loguru import logger
from sqlalchemy import text

from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod


def recommend_mods_with_session(session, *, tags: list[str], mc_version: str | None = None,
                                loader: str | None = None, top_k: int = 5,
                                exclude_ids: list[str] | None = None) -> list[dict]:
    """Tag-based mod recommendation using in-memory Python matching.

    Avoids MySQL-specific JSON functions — works with both SQLite and MySQL.
    """
    if not tags:
        return []

    q = session.query(Mod).filter(Mod.tags.isnot(None))
    if loader:
        q = q.filter(Mod.loader.contains(loader))
    rows = q.all()

    scored = []
    for m in rows:
        if not m.tags or "genres" not in m.tags:
            continue
        if exclude_ids and m.mod_id in exclude_ids:
            continue
        if mc_version:
            versions = m.mc_versions or []
            if mc_version not in versions:
                continue

        genres = m.tags.get("genres", [])
        if not isinstance(genres, list):
            genres = [genres] if genres else []

        match_count = sum(1 for t in tags if t in genres)
        if match_count > 0:
            scored.append((match_count, m))

    scored.sort(key=lambda x: -x[0])
    result = []
    for _, m in scored[:top_k]:
        tags_val = m.tags
        if isinstance(tags_val, str):
            import json
            try:
                tags_val = json.loads(tags_val)
            except Exception:
                tags_val = {}
        result.append({
            "mod_id": m.mod_id,
            "name_zh": m.name_zh,
            "name_en": m.name_en,
            "mcmod_url": m.mcmod_url,
            "tags": tags_val,
            "description": (m.description or "")[:200],
            "match_score": getattr(m, "score", 1),
        })
    return result


def recommend_mods(tags: list[str], mc_version: str | None = None,
                   loader: str | None = None, top_k: int = 5,
                   exclude_ids: list[str] | None = None) -> list[dict]:
    try:
        with SessionLocal() as session:
            return recommend_mods_with_session(session, tags=tags, mc_version=mc_version,
                                               loader=loader, top_k=top_k, exclude_ids=exclude_ids)
    except Exception as e:
        logger.exception("recommend_mods failed")
        return [{"error": str(e)}]
