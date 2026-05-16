import pytest

from agents.answerer import AnswererAgent
from agents.router import RouterAgent
from agents.workflow import McmodWorkflow
from kb.retriever import VectorRetriever


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_create_intro():
    wf = McmodWorkflow(
        router=RouterAgent(),
        retriever=VectorRetriever(),
        answerer=AnswererAgent(),
    )
    result = await wf.run(query="机械动力是什么？")
    assert result["intent"] == "kb_query"
    assert len(result["chunks"]) > 0
    assert "[来源" in result["answer"] or "未在知识库" in result["answer"]
