import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.storage.db import Base
from pipeline.storage.models import ItemAlias, Mod


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


def test_create_mod(session):
    m = Mod(mod_id="create", name_zh="机械动力", mcmod_url="https://...")
    session.add(m)
    session.commit()
    assert session.query(Mod).filter_by(mod_id="create").first().name_zh == "机械动力"


def test_create_alias(session):
    a = ItemAlias(mod_id="create", name_zh="动力轴", name_en="Shaft")
    session.add(a)
    session.commit()
    assert session.query(ItemAlias).count() == 1
