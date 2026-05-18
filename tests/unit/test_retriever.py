"""Test HybridRetriever's RRF merge logic and keyword search wiring."""
from unittest.mock import MagicMock

from kb.retriever import HybridRetriever
from kb.schemas import Chunk, ChunkMetadata


def _make_chunk(mod_id: str, text: str, url: str = "https://x") -> Chunk:
    md = ChunkMetadata(mod_id=mod_id, mod_name_zh=mod_id, section="intro",
                       source_url=url, title="t")
    return Chunk(text=text, metadata=md, score=0.5)


def test_hybrid_retriever_delegates_to_vector_retriever():
    fake_vec = MagicMock()
    fake_vec.retrieve.return_value = [_make_chunk("create", "机械动力是…")]

    r = HybridRetriever(vector_retriever=fake_vec)
    # Stub keyword search to isolate vector path
    r._keyword_search = lambda *a, **kw: []

    chunks = r.retrieve("机械动力", top_k=4)
    assert fake_vec.retrieve.called
    assert len(chunks) == 1
    assert chunks[0].metadata.mod_id == "create"


def test_rrf_merge_combines_two_lists():
    a = [_make_chunk("m1", "a1", "url1"), _make_chunk("m2", "a2", "url2")]
    b = [_make_chunk("m2", "a2", "url2"), _make_chunk("m3", "a3", "url3")]
    merged = HybridRetriever._rrf_merge(a, b, k=60, top_k=3)
    assert len(merged) == 3
    ids = [c.metadata.mod_id for c in merged]
    assert "m2" in ids


def test_keyword_search_returns_empty_for_no_keywords():
    r = HybridRetriever(vector_retriever=MagicMock())
    assert r._keyword_search(" !@#", top_k=4) == []
