from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    pass


if settings.use_mysql:
    _url = settings.mysql_url
    _kwargs = {"pool_pre_ping": True, "echo": False}
else:
    _url = f"sqlite:///{settings.sqlite_path}"
    _kwargs = {"echo": False, "connect_args": {"check_same_thread": False}}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
