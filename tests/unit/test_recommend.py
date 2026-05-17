import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.storage.db import Base
from pipeline.storage.models import Mod
from tools.recommend_mods import recommend_mods_with_session


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(Mod(mod_id="1", name_zh="恐怖模组A", mcmod_url="x", mc_versions=["1.20.1"],
                  loader="Forge", tags={"genres": ["恐怖", "冒险"], "mood": "恐怖"}))
        s.add(Mod(mod_id="2", name_zh="魔法模组B", mcmod_url="x", mc_versions=["1.19.2"],
                  loader="Fabric", tags={"genres": ["魔法"], "mood": "治愈"}))
        s.add(Mod(mod_id="3", name_zh="科技模组C", mcmod_url="x", mc_versions=["1.20.1"],
                  loader="Forge", tags={"genres": ["科技"], "mood": "探索"}))
        s.add(Mod(mod_id="4", name_zh="无标签D", mcmod_url="x", tags=None))
        s.commit()
        yield s


def test_recommend_by_genre(session):
    result = recommend_mods_with_session(session, tags=["恐怖"], top_k=3)
    assert len(result) >= 1
    assert result[0]["mod_id"] == "1"


def test_recommend_empty_tags(session):
    result = recommend_mods_with_session(session, tags=["不存在"], top_k=3)
    assert result == []


def test_recommend_empty_input(session):
    result = recommend_mods_with_session(session, tags=[], top_k=3)
    assert result == []
