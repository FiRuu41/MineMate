from unittest.mock import MagicMock

import pytest

from agents.workflow import McmodWorkflow
from kb.schemas import Chunk, ChunkMetadata


def _chunk(text="hi"):
    md = ChunkMetadata(
        mod_id="create", mod_name_zh="机械动力", section="intro",
        mc_version="1.20.1", source_url="u", title="t",
    )
    return Chunk(text=text, metadata=md, score=0.9)


@pytest.mark.asyncio
async def test_workflow_kb_query():
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "kb_query", "entities": {"mod_name": "机械动力"}}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = [_chunk("机械动力是工程模组")]
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "机械动力是工程模组 [来源1]"

    wf = McmodWorkflow(router=fake_router, retriever=fake_retriever, answerer=fake_answerer)
    result = await wf.run(query="什么是机械动力")
    assert "[来源1]" in result["answer"]
    assert result["intent"] == "kb_query"
    assert len(result["chunks"]) == 1


@pytest.mark.asyncio
async def test_workflow_chitchat_skips_retrieve():
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "chitchat", "entities": {}}
    fake_retriever = MagicMock()
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "你好！"
    wf = McmodWorkflow(router=fake_router, retriever=fake_retriever, answerer=fake_answerer)
    result = await wf.run(query="你好")
    assert result["intent"] == "chitchat"
    fake_retriever.retrieve.assert_not_called()
    assert result["answer"] == "你好！"
