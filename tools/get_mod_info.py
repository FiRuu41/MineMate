"""Look up mod metadata from MySQL."""
from loguru import logger

from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod


def get_mod_info(mod_name_or_id: str) -> dict:
    try:
        with SessionLocal() as session:
            m = session.get(Mod, mod_name_or_id)
            if not m:
                m = session.query(Mod).filter(
                    (Mod.name_zh == mod_name_or_id) | (Mod.name_en == mod_name_or_id)
                ).first()
            if not m:
                return {"error": f"mod '{mod_name_or_id}' not found"}
            return {
                "mod_id": m.mod_id,
                "name_zh": m.name_zh,
                "name_en": m.name_en,
                "mcmod_url": m.mcmod_url,
                "loader": m.loader,
                "mc_versions": m.mc_versions or [],
                "author": m.author,
                "description": (m.description or "")[:500],
            }
    except Exception as e:
        logger.exception("get_mod_info failed")
        return {"error": str(e)}
