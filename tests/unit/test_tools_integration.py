from unittest.mock import MagicMock, patch

import pytest

from agents.workflow import McmodWorkflow
from kb.schemas import Chunk, ChunkMetadata


def _chunk(text="hi"):
    md = ChunkMetadata(mod_id="x", mod_name_zh="x", section="intro", source_url="u", title="t")
    return Chunk(text=text, metadata=md)


@pytest.mark.asyncio
async def test_workflow_mod_info():
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "mod_info_query", "entities": {"mod_name": "Create"}}
    fake_retriever = MagicMock()
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "Create supports 1.20.1"
    fake_critic = MagicMock()
    fake_critic.review.return_value = {"pass": True, "reason": "", "suggestion": ""}

    with patch("tools.get_mod_info.get_mod_info") as mock_get:
        mock_get.return_value = {"mod_id": "2021", "name_zh": "机械动力", "mc_versions": ["1.20.1"]}
        wf = McmodWorkflow(router=fake_router, retriever=fake_retriever, answerer=fake_answerer, critic=fake_critic)
        result = await wf.run(query="Create supports which versions")
        assert result["intent"] == "mod_info_query"
        assert result["tool_results"]["mod_info"]["name_zh"] == "机械动力"


@pytest.mark.asyncio
async def test_workflow_web_fallback():
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "web_fallback", "entities": {}}
    fake_retriever = MagicMock()
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "Found on mcmod: ..."
    fake_critic = MagicMock()
    fake_critic.review.return_value = {"pass": True, "reason": "", "suggestion": ""}

    with patch("tools.web_search_mcmod.web_search_mcmod") as mock_search:
        mock_search.return_value = [{"class_id": "2021", "url": "https://...", "snippet": "机械动力"}]
        wf = McmodWorkflow(router=fake_router, retriever=fake_retriever, answerer=fake_answerer, critic=fake_critic)
        result = await wf.run(query="latest mod news")
        assert result["intent"] == "web_fallback"
        assert len(result["tool_results"]["web_results"]) == 1
