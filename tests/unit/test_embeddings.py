import pytest

from llm.embeddings import get_embedder


@pytest.mark.slow
def test_embedder_returns_vectors():
    """Requires BGE-M3 model download (~2GB). Marked slow; skip by default."""
    e = get_embedder()
    v = e.get_text_embedding("hello world")
    assert isinstance(v, list)
    assert len(v) > 100
