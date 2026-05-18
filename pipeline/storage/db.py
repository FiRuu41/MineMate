from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    pass


_path = settings.resolved_sqlite_path
_path.parent.mkdir(parents=True, exist_ok=True)
_url = f"sqlite:///{_path}"
_kwargs = {"echo": False, "connect_args": {"check_same_thread": False}}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
