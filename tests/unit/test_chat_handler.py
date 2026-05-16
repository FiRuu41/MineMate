from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chat_handler import ChatHandler
from kb.schemas import Chunk, ChunkMetadata


def _chunk():
    md = ChunkMetadata(
        mod_id="create", mod_name_zh="机械动力", section="intro",
        mc_version="1.20.1", source_url="u", title="t",
    )
    return Chunk(text="机械动力是…", metadata=md, score=0.9)


@pytest.mark.asyncio
async def test_chat_returns_answer_and_debug():
    fake_wf = MagicMock()
    fake_wf.run = AsyncMock(return_value={
        "intent": "kb_query",
        "answer": "机械动力是工程模组 [来源1]",
        "chunks": [_chunk()],
    })
    h = ChatHandler(workflow=fake_wf)
    answer, debug = await h.chat("什么是机械动力")
    assert "[来源1]" in answer
    assert "kb_query" in debug
    assert "机械动力" in debug
