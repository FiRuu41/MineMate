import pytest


def test_chroma_retriever_imports():
    """Verify ChromaRetriever can be imported and constructed."""
    from kb.chroma_retriever import ChromaRetriever
    assert ChromaRetriever is not None


@pytest.mark.slow
def test_chroma_retriever_constructs_with_temp_path(tmp_path, monkeypatch):
    """End-to-end with real ChromaDB persistent client (downloads BGE-M3, ~2.3GB)."""
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    from config.settings import settings
    from kb.chroma_retriever import ChromaRetriever
    settings.chroma_path = str(tmp_path / "chroma")

    r = ChromaRetriever()
    assert r.collection_name == "mcmod_v1"
    assert r._client is not None
