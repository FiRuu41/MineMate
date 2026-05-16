from datetime import datetime

from sqlalchemy.orm import Session

from pipeline.storage.models import Mod


def upsert_mod(
    session: Session,
    *,
    mod_id: str,
    name_zh: str,
    mcmod_url: str,
    name_en: str | None = None,
    loader: str | None = None,
    mc_versions: list[str] | None = None,
    author: str | None = None,
    description: str | None = None,
) -> Mod:
    m = session.get(Mod, mod_id)
    if m is None:
        m = Mod(mod_id=mod_id)
        session.add(m)
    m.name_zh = name_zh
    m.name_en = name_en
    m.mcmod_url = mcmod_url
    m.loader = loader
    m.mc_versions = mc_versions or []
    m.author = author
    m.description = description
    m.updated_at = datetime.utcnow()
    return m
