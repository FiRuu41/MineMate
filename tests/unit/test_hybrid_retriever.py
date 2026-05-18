
from kb.retriever import HybridRetriever
from kb.schemas import Chunk, ChunkMetadata


def _chunk(text="test", mod_id="x", score=0.8):
    md = ChunkMetadata(mod_id=mod_id, mod_name_zh="X", section="intro",
                       source_url="http://x", title="T")
    return Chunk(text=text, metadata=md, score=score)


def test_rrf_merge_dedup_and_sort():
    c1 = _chunk("mechanical power source", "create", 0.9)
    c2 = _chunk("botania flower magic", "botania", 0.7)
    c3 = _chunk("mechanical engineering", "create", 0.6)

    merged = HybridRetriever._rrf_merge(
        [c1, c3],  # vector: mechanical
        [c2],      # keyword: flower
        top_k=3,
    )
    assert len(merged) == 3
    # c1 should rank highest (appears in vector rank 1)
    assert merged[0].text == "mechanical power source"


def test_rrf_merge_handles_empty_keyword():
    c1 = _chunk("a", "x", 0.9)
    merged = HybridRetriever._rrf_merge([c1], [], top_k=3)
    assert len(merged) == 1
    assert merged[0].text == "a"


def test_rrf_merge_respects_top_k():
    chunks = [_chunk(str(i), str(i), 0.9 - i * 0.1) for i in range(10)]
    merged = HybridRetriever._rrf_merge(chunks, [], top_k=3)
    assert len(merged) == 3
