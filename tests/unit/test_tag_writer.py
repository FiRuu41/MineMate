import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.storage.db import Base
from pipeline.storage.models import Mod
from pipeline.storage.mysql_writer import update_mod_integrations, update_mod_tags


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(Mod(mod_id="t1", name_zh="x", mcmod_url="x"))
        s.commit()
        yield s


def test_update_tags(session):
    tags = {"genres": ["魔法"], "themes": ["奇幻"], "mood": "治愈", "difficulty": "休闲"}
    update_mod_tags(session, "t1", tags)
    m = session.get(Mod, "t1")
    assert m.tags["genres"] == ["魔法"]


def test_update_integrations(session):
    integrations = [{"mod_id": "2021", "mod_name_zh": "机械动力", "evidence": "兼容"}]
    update_mod_integrations(session, "t1", integrations)
    m = session.get(Mod, "t1")
    assert len(m.known_integrations) == 1
