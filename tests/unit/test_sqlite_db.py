import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pipeline.storage.db import Base
from pipeline.storage.models import Mod


def _make_session():
    """Create a temp-file-based session, isolated from production DB."""
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    eng = create_engine(f"sqlite:///{tmp}", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng, autoflush=False)()


def test_sqlite_creates_tables():
    s = _make_session()
    m = Mod(mod_id="t1", name_zh="测试", mcmod_url="x")
    s.add(m)
    s.commit()
    assert s.get(Mod, "t1").name_zh == "测试"


def test_sqlite_json_column():
    s = _make_session()
    m = Mod(mod_id="t2", name_zh="x2", mcmod_url="x",
            mc_versions=["1.20.1", "1.19.2"],
            tags={"genres": ["科技"]})
    s.add(m)
    s.commit()
    m2 = s.get(Mod, "t2")
    assert "1.20.1" in m2.mc_versions
    assert m2.tags["genres"] == ["科技"]
