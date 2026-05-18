from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Base(DeclarativeBase):
    pass


if settings.use_mysql:
    _url = settings.mysql_url
    _kwargs = {"pool_pre_ping": True, "echo": False}
else:
    _path = _PROJECT_ROOT / settings.sqlite_path
    _path.parent.mkdir(parents=True, exist_ok=True)
    _url = f"sqlite:///{_path}"
    _kwargs = {"echo": False, "connect_args": {"check_same_thread": False}}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
