import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline.storage.db import Base
from pipeline.storage.models import Mod
from tools.compatibility import (
    check_mod_compatibility_with_session,
    get_compatible_mods_with_session,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(Mod(mod_id="a", name_zh="ModA", mcmod_url="x",
                  mc_versions=["1.20.1", "1.19.2"],
                  loader="Forge / Fabric",
                  known_integrations=[
                      {"mod_name_zh": "ModB", "evidence": "integrates with B"}
                  ]))
        s.add(Mod(mod_id="b", name_zh="ModB", mcmod_url="x",
                  mc_versions=["1.20.1"], loader="Forge"))
        s.commit()
        yield s


def test_get_compatible_mods(session):
    result = get_compatible_mods_with_session(session, "a")
    assert len(result) == 1
    assert result[0]["mod_name_zh"] == "ModB"
    assert result[0]["matched_mod_id"] == "b"


def test_check_compatible(session):
    result = check_mod_compatibility_with_session(session, "a", "b")
    assert result["compatible"] is True
    assert "1.20.1" in result["common_mc_versions"]
    assert result["known_integration"] is True


def test_check_not_compatible(session):
    result = check_mod_compatibility_with_session(session, "b", "a")
    assert result["compatible"] is True
    assert "1.20.1" in result["common_mc_versions"]


def test_check_missing_mod(session):
    result = check_mod_compatibility_with_session(session, "a", "nonexistent")
    assert result["compatible"] is False
    assert "error" in result
