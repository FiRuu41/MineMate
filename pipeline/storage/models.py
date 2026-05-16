from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.storage.db import Base


class Mod(Base):
    __tablename__ = "mods"

    mod_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mcmod_url: Mapped[str] = mapped_column(String(256))
    loader: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mc_versions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ItemAlias(Base):
    __tablename__ = "item_aliases"
    __table_args__ = (UniqueConstraint("mod_id", "name_en", name="uq_mod_name_en"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mod_id: Mapped[str] = mapped_column(String(64), index=True)
    name_zh: Mapped[str] = mapped_column(String(128), index=True)
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
