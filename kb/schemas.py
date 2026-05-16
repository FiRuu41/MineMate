from typing import Literal

from pydantic import BaseModel, Field

Section = Literal["intro", "tutorial", "item", "recipe"]


class ChunkMetadata(BaseModel):
    mod_id: str
    mod_name_zh: str
    section: Section
    mc_version: str | None = None
    source_url: str
    title: str


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    score: float | None = None


class ModSeed(BaseModel):
    mod_id: str
    name_zh: str
    name_en: str | None = None
    mcmod_url: str
    mc_versions: list[str] = Field(default_factory=list)
