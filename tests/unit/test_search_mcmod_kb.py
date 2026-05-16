from unittest.mock import MagicMock

from kb.schemas import Chunk, ChunkMetadata
from tools.search_mcmod_kb import search_mcmod_kb_with


def test_search_returns_dicts():
    fake = MagicMock()
    fake.retrieve.return_value = [
        Chunk(
            text="hi",
            metadata=ChunkMetadata(
                mod_id="create", mod_name_zh="机械动力", section="intro",
                mc_version="1.20.1", source_url="u", title="t",
            ),
            score=0.9,
        )
    ]
    out = search_mcmod_kb_with(fake, query="x", top_k=4)
    assert isinstance(out, list)
    assert out[0]["score"] == 0.9
    assert out[0]["mod_name_zh"] == "机械动力"


def test_search_error_returns_error_dict():
    fake = MagicMock()
    fake.retrieve.side_effect = RuntimeError("boom")
    out = search_mcmod_kb_with(fake, query="x")
    assert isinstance(out, dict)
    assert "error" in out
