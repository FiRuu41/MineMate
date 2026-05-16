from unittest.mock import MagicMock

from kb.retriever import VectorRetriever


def test_retrieve_calls_qdrant_and_maps_results():
    fake_qclient = MagicMock()
    point = MagicMock()
    point.score = 0.87
    point.payload = {
        "mod_id": "create",
        "mod_name_zh": "机械动力",
        "section": "intro",
        "mc_version": "1.20.1",
        "source_url": "https://x",
        "title": "简介",
        "text": "机械动力是…",
    }
    fake_qclient.search.return_value = [point]
    fake_embedder = MagicMock()
    fake_embedder.get_text_embedding.return_value = [0.1] * 8

    r = VectorRetriever(client=fake_qclient, embedder=fake_embedder, collection="t")
    chunks = r.retrieve("机械动力是什么", top_k=4)
    assert len(chunks) == 1
    assert chunks[0].score == 0.87
    assert chunks[0].text == "机械动力是…"
    assert chunks[0].metadata.mod_id == "create"


def test_retrieve_with_mod_filter():
    fake_qclient = MagicMock()
    fake_qclient.search.return_value = []
    fake_embedder = MagicMock()
    fake_embedder.get_text_embedding.return_value = [0.1] * 8

    r = VectorRetriever(client=fake_qclient, embedder=fake_embedder, collection="t")
    r.retrieve("q", top_k=4, mod_id="create")
    kwargs = fake_qclient.search.call_args.kwargs
    assert kwargs["query_filter"] is not None
