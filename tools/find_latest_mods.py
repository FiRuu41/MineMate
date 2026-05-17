"""Find latest/recently added mods, optionally filtered by tags/version."""
from sqlalchemy import desc, text

from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod


def find_latest_mods(
    tags: list[str] | None = None,
    mc_version: str | None = None,
    loader: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Return recently added mods, optionally filtered.

    Uses class_id (mod_id as integer) as proxy for recency.
    """
    try:
        with SessionLocal() as session:
            q = session.query(Mod).filter(Mod.tags.isnot(None), Mod.description.isnot(None))
            if mc_version:
                q = q.filter(text("JSON_CONTAINS(mc_versions, :ver)")).params(ver=f'"{mc_version}"')
            if loader:
                q = q.filter(Mod.loader.contains(loader))
            # Sort by mod_id as integer (higher = newer on mcmod)
            rows = q.order_by(desc(text("CAST(mod_id AS UNSIGNED)"))).limit(top_k * 3).all()

            # If tags specified, filter in-memory (MySQL JSON matching is complex)
            results = []
            for m in rows:
                score = _tag_match_score(m.tags, tags) if tags else 0
                if tags and score == 0:
                    continue
                results.append({
                    "mod_id": m.mod_id,
                    "name_zh": m.name_zh,
                    "name_en": m.name_en,
                    "mcmod_url": m.mcmod_url,
                    "loader": m.loader,
                    "mc_versions": m.mc_versions or [],
                    "tags": m.tags,
                    "description": (m.description or "")[:300],
                    "match_score": score,
                })
                if len(results) >= top_k:
                    break
            return results
    except Exception:
        return [{"error": "query failed"}]


def _tag_match_score(mod_tags: dict | None, query_tags: list[str] | None) -> int:
    if not mod_tags or not query_tags:
        return 0
    genres = mod_tags.get("genres", [])
    themes = mod_tags.get("themes", [])
    mood = mod_tags.get("mood", "")
    all_tags = list(genres) + list(themes) + ([mood] if mood else [])
    return sum(1 for t in query_tags if t in all_tags)
