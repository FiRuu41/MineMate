from pipeline.storage.db import Base, SessionLocal, engine


def test_sqlite_creates_tables():
    Base.metadata.create_all(engine)
    from pipeline.storage.models import Mod
    with SessionLocal() as s:
        m = Mod(mod_id="t1", name_zh="测试", mcmod_url="x")
        s.add(m)
        s.commit()
        assert s.get(Mod, "t1").name_zh == "测试"


def test_sqlite_json_column():
    """SQLite stores JSON as text, SQLAlchemy auto-serializes."""
    from pipeline.storage.models import Mod
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        m = Mod(mod_id="t2", name_zh="x2", mcmod_url="x",
                mc_versions=["1.20.1", "1.19.2"],
                tags={"genres": ["科技"]})
        s.add(m)
        s.commit()
        m2 = s.get(Mod, "t2")
        assert "1.20.1" in m2.mc_versions
        assert m2.tags["genres"] == ["科技"]
