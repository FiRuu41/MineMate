import pytest

from kb.schemas import Chunk, ChunkMetadata
from pipeline.storage.qdrant_writer import QdrantWriter


@pytest.fixture
def writer():
    w = QdrantWriter(collection="mcmod_test")
    w.recreate(dim=8)
    yield w
    w.delete_collection()


@pytest.mark.integration
def test_upsert_and_count(writer):
    md = ChunkMetadata(mod_id="create", mod_name_zh="机械动力", section="intro", source_url="x", title="t")
    chunks = [Chunk(text=f"text {i}", metadata=md) for i in range(3)]
    vectors = [[0.0] * 8 for _ in chunks]
    writer.upsert(chunks, vectors)
    assert writer.count() == 3


@pytest.mark.integration
def test_delete_by_mod(writer):
    md_a = ChunkMetadata(mod_id="a", mod_name_zh="A", section="intro", source_url="x", title="t")
    md_b = ChunkMetadata(mod_id="b", mod_name_zh="B", section="intro", source_url="x", title="t")
    writer.upsert([Chunk(text="x", metadata=md_a)], [[0.0] * 8])
    writer.upsert([Chunk(text="y", metadata=md_b)], [[0.0] * 8])
    writer.delete_by_mod_id("a")
    assert writer.count() == 1
