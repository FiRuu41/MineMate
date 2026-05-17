from loguru import logger
from sqlalchemy import text

from pipeline.storage.db import SessionLocal


def recommend_mods_with_session(session, *, tags: list[str], mc_version: str | None = None,
                                loader: str | None = None, top_k: int = 5) -> list[dict]:
    if not tags:
        return []
    conds = ["m.tags IS NOT NULL"]
    params: dict = {"taglist": tuple(tags), "limit": top_k}
    if mc_version:
        conds.append("JSON_CONTAINS(m.mc_versions, :mcver)")
        params["mcver"] = f'"{mc_version}"'
    if loader:
        conds.append("m.loader LIKE :ldr")
        params["ldr"] = f"%{loader}%"
    where = " AND ".join(conds)

    # MySQL JSON_TABLE – compatible; for SQLite tests we use a simpler fallback
    try:
        sql = text(f"""
            SELECT m.mod_id, m.name_zh, m.name_en, m.mcmod_url, m.tags, m.description,
                   (SELECT COUNT(*) FROM JSON_TABLE(
                       JSON_EXTRACT(m.tags, '$.genres'), '$[*]' COLUMNS(v VARCHAR(64) PATH '$')
                   ) t WHERE t.v IN :taglist
                   ) AS score
            FROM mods m
            WHERE {where}
            HAVING score > 0
            ORDER BY score DESC
            LIMIT :limit
        """)
        rows = session.execute(sql, params).fetchall()
    except Exception:
        logger.exception("MySQL JSON_TABLE failed, trying in-memory fallback")
        rows = _fallback_search(session, tags, mc_version, loader, top_k)

    return [
        {
            "mod_id": r.mod_id,
            "name_zh": r.name_zh,
            "name_en": r.name_en,
            "mcmod_url": r.mcmod_url,
            "tags": r.tags,
            "description": (r.description or "")[:200],
            "match_score": r.score if hasattr(r, "score") else 1,
        }
        for r in rows
    ]


def _fallback_search(session, tags, mc_version, loader, top_k):
    """In-memory tag matching (works on SQLite for tests)."""
    from pipeline.storage.models import Mod

    q = session.query(Mod).filter(Mod.tags.isnot(None))
    rows = q.all()
    scored = []
    for m in rows:
        if not m.tags or "genres" not in m.tags:
            continue
        if mc_version and mc_version not in (m.mc_versions or []):
            continue
        if loader and loader.lower() not in (m.loader or "").lower():
            continue
        score = sum(1 for t in tags if t in m.tags.get("genres", []))
        if score > 0:
            scored.append((score, m))
    scored.sort(key=lambda x: -x[0])
    return [m for _, m in scored[:top_k]]


def recommend_mods(tags: list[str], mc_version: str | None = None,
                   loader: str | None = None, top_k: int = 5) -> list[dict]:
    try:
        with SessionLocal() as session:
            return recommend_mods_with_session(session, tags=tags, mc_version=mc_version,
                                               loader=loader, top_k=top_k)
    except Exception as e:
        logger.exception("recommend_mods failed")
        return [{"error": str(e)}]
