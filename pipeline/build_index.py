"""CLI: chunk intro descriptions + embed + upsert to Qdrant."""
import argparse

from loguru import logger
from sqlalchemy import select

from config.logging import new_trace_id, setup_logging
from config.settings import settings
from kb.schemas import ChunkMetadata
from llm.embeddings import get_embedder
from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod
from pipeline.storage.qdrant_writer import QdrantWriter
from pipeline.structure import intro_to_chunks


def build_for_mod(mod: Mod, writer: QdrantWriter, embedder) -> int:
    if not mod.description:
        logger.warning("[{}] empty description, skip", mod.mod_id)
        return 0
    mc_ver = (mod.mc_versions or [None])[0]
    metadata = ChunkMetadata(
        mod_id=mod.mod_id,
        mod_name_zh=mod.name_zh,
        section="intro",
        mc_version=mc_ver,
        source_url=mod.mcmod_url,
        title=f"{mod.name_zh} 简介",
    )
    chunks = intro_to_chunks(mod.description, metadata, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        return 0
    vectors = [embedder.get_text_embedding(c.text) for c in chunks]
    writer.delete_by_mod_id(mod.mod_id)
    writer.upsert(chunks, vectors)
    logger.info("[{}] indexed {} chunks", mod.mod_id, len(chunks))
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", help="single mod_id to rebuild")
    args = parser.parse_args()

    setup_logging()
    new_trace_id()

    embedder = get_embedder()
    writer = QdrantWriter()

    with SessionLocal() as session:
        q = select(Mod)
        if args.mod:
            q = q.where(Mod.mod_id == args.mod)
        mods = session.execute(q).scalars().all()

    total = 0
    for m in mods:
        total += build_for_mod(m, writer, embedder)
    logger.info("indexed {} chunks across {} mods", total, len(mods))


if __name__ == "__main__":
    main()
