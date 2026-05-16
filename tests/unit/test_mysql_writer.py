import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.storage.db import Base
from pipeline.storage.models import Mod
from pipeline.storage.mysql_writer import upsert_mod


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def test_upsert_creates(session):
    upsert_mod(
        session,
        mod_id="create",
        name_zh="机械动力",
        name_en="Create",
        mcmod_url="https://...",
        loader="Forge",
        mc_versions=["1.20.1"],
        author="simibubi",
        description="desc",
    )
    session.commit()
    m = session.query(Mod).filter_by(mod_id="create").one()
    assert m.name_zh == "机械动力"


def test_upsert_updates(session):
    upsert_mod(session, mod_id="create", name_zh="旧名", mcmod_url="x")
    session.commit()
    upsert_mod(session, mod_id="create", name_zh="机械动力", mcmod_url="x")
    session.commit()
    assert session.query(Mod).filter_by(mod_id="create").one().name_zh == "机械动力"
