"""Compatibility lookup tools."""
from loguru import logger
from sqlalchemy.orm import Session

from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod


def _intersect_loader(a: str | None, b: str | None) -> str | None:
    if not a or not b:
        return a or b
    a_set = {x.strip() for x in a.replace("/", " ").split()}
    b_set = {x.strip() for x in b.replace("/", " ").split()}
    common = a_set & b_set
    return ", ".join(sorted(common)) if common else None


def get_compatible_mods_with_session(session: Session, mod_id: str) -> list[dict]:
    m = session.get(Mod, mod_id)
    if not m:
        return []
    results = []
    if m.known_integrations:
        for integ in m.known_integrations:
            linked_name = integ.get("mod_name_zh", "")
            linked = session.query(Mod).filter(
                (Mod.name_zh == linked_name) | (Mod.name_en == linked_name)
            ).first()
            results.append({
                "mod_name_zh": linked_name,
                "matched_mod_id": linked.mod_id if linked else None,
                "common_mc_versions":
                    list(set(m.mc_versions or []) & set(linked.mc_versions or [])) if linked else [],
                "common_loader": _intersect_loader(m.loader, linked.loader) if linked else None,
                "evidence": integ.get("evidence", ""),
                "source_url": integ.get("source_url", ""),
            })
        return results
    # Fallback: find mods sharing MC versions + loader (no explicit integration data)
    if m.mc_versions:
        from sqlalchemy import text as sqlt
        for ver in (m.mc_versions or [])[:3]:
            rows = session.execute(
                sqlt("SELECT mod_id, name_zh, name_en, mc_versions, loader FROM mods "
                     "WHERE mod_id != :mid AND JSON_CONTAINS(mc_versions, :ver) LIMIT 10"),
                {"mid": mod_id, "ver": f'"{ver}"'},
            ).fetchall()
            for row in rows:
                common_ver = list(set(m.mc_versions or []) & set(row.mc_versions or []))
                common_ldr = _intersect_loader(m.loader, row.loader)
                results.append({
                    "mod_name_zh": row.name_zh,
                    "matched_mod_id": row.mod_id,
                    "common_mc_versions": common_ver,
                    "common_loader": common_ldr,
                    "evidence": f"共同支持 MC {ver}",
                    "source_url": "",
                })
            if len(results) >= 10:
                break
    return results[:10]


def check_mod_compatibility_with_session(session: Session, mod_a: str, mod_b: str) -> dict:
    a = session.get(Mod, mod_a)
    b = session.get(Mod, mod_b)
    if not a or not b:
        return {"compatible": False, "error": "mod not found"}

    common_versions = list(set(a.mc_versions or []) & set(b.mc_versions or []))
    common_loader = _intersect_loader(a.loader, b.loader)
    known = False
    evidence = None
    if a.known_integrations:
        for integ in a.known_integrations:
            if integ.get("mod_name_zh") in (b.name_zh, b.name_en):
                known = True
                evidence = integ.get("evidence")
                break

    return {
        "compatible": len(common_versions) > 0 or known,
        "common_mc_versions": common_versions,
        "common_loader": common_loader,
        "known_integration": known,
        "evidence": evidence,
    }


def get_compatible_mods(mod_id: str) -> list[dict]:
    try:
        with SessionLocal() as session:
            return get_compatible_mods_with_session(session, mod_id)
    except Exception as e:
        logger.exception("get_compatible_mods failed")
        return [{"error": str(e)}]


def check_mod_compatibility(mod_a: str, mod_b: str) -> dict:
    try:
        with SessionLocal() as session:
            return check_mod_compatibility_with_session(session, mod_a, mod_b)
    except Exception as e:
        logger.exception("check_mod_compatibility failed")
        return {"error": str(e)}
