"""Tests for McmodWorkflow critic retry loop integration."""
from unittest.mock import MagicMock

import pytest

from agents.workflow import McmodWorkflow
from kb.schemas import Chunk, ChunkMetadata


def _chunk(text="机械动力是一个工程模组。"):
    md = ChunkMetadata(
        mod_id="create", mod_name_zh="机械动力", section="intro",
        mc_version="1.20.1", source_url="http://example.com", title="测试",
    )
    return Chunk(text=text, metadata=md, score=0.9)


@pytest.mark.asyncio
async def test_critic_passes():
    """When critic returns pass=True on first attempt, answer is returned normally."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "kb_query", "entities": {"mod_name": "机械动力"}}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = [_chunk("机械动力是工程模组")]
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "机械动力是一个工程模组 [来源1]"
    fake_critic = MagicMock()
    fake_critic.review.return_value = {"pass": True, "reason": "good", "suggestion": ""}

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    result = await wf.run(query="什么是机械动力")

    assert "⚠️" not in result["answer"]
    assert "[来源1]" in result["answer"]
    assert result["retry_count"] == 0
    assert result["intent"] == "kb_query"
    # Critic called exactly once, retriever called exactly once
    assert fake_critic.review.call_count == 1
    assert fake_retriever.retrieve.call_count == 1


@pytest.mark.asyncio
async def test_critic_fails_then_passes():
    """First critic review fails, retry with feedback succeeds."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "kb_query", "entities": {}}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = [_chunk("机械动力是工程模组")]
    fake_answerer = MagicMock()
    fake_answerer.answer.side_effect = [
        "bad answer with hallucination",
        "good answer with citation [来源1]",
    ]
    fake_critic = MagicMock()
    fake_critic.review.side_effect = [
        {"pass": False, "reason": "幻觉", "suggestion": "检查参考资料重新回答"},
        {"pass": True, "reason": "good now", "suggestion": ""},
    ]

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    result = await wf.run(query="什么是机械动力")

    assert "⚠️" not in result["answer"]
    assert result["answer"] == "good answer with citation [来源1]"
    assert result["retry_count"] == 1
    # Critic called twice, retriever called twice (initial + 1 retry)
    assert fake_critic.review.call_count == 2
    assert fake_retriever.retrieve.call_count == 2

    # Verify retriever was called with expanded top_k on retry
    retriever_calls = fake_retriever.retrieve.call_args_list
    # First call: original query, top_k=settings.top_k (8)
    assert retriever_calls[0].kwargs["top_k"] == 8
    # Second call: query with feedback, top_k=settings.top_k * 2 (16)
    assert "补充信息" in retriever_calls[1].args[0]
    assert retriever_calls[1].kwargs["top_k"] == 16


@pytest.mark.asyncio
async def test_critic_fails_max_retries():
    """After 3 attempts (initial + 2 retries) all fail, return with warning prefix."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "kb_query", "entities": {}}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = [_chunk()]
    fake_answerer = MagicMock()
    fake_answerer.answer.side_effect = ["answer1", "answer2", "answer3"]
    fake_critic = MagicMock()
    fake_critic.review.return_value = {"pass": False, "reason": "still bad", "suggestion": "fix again"}

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    result = await wf.run(query="什么是机械动力")

    assert result["answer"].startswith("⚠️ 此回答未通过自动校验，仅供参考")
    assert "answer3" in result["answer"]
    assert result["retry_count"] == 2
    # Critic called 3 times (attempts 0, 1, 2)
    assert fake_critic.review.call_count == 3
    # Retriever called 3 times (initial + retry1 + retry2)
    assert fake_retriever.retrieve.call_count == 3

    # Verify top_k escalated correctly
    retriever_calls = fake_retriever.retrieve.call_args_list
    assert retriever_calls[0].kwargs["top_k"] == 8   # default
    assert retriever_calls[1].kwargs["top_k"] == 16  # top_k * 2
    assert retriever_calls[2].kwargs["top_k"] == 24  # top_k * 3


@pytest.mark.asyncio
async def test_critic_only_for_kb_query():
    """Recommendation intent skips critic entirely."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "recommendation", "entities": {"tags": ["tech"]}}
    fake_retriever = MagicMock()
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "推荐机械动力、应用能源等模组"
    fake_critic = MagicMock()

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    result = await wf.run(query="推荐一些科技模组")

    assert fake_critic.review.call_count == 0
    assert result["answer"] == "推荐机械动力、应用能源等模组"
    assert result["retry_count"] == 0


@pytest.mark.asyncio
async def test_critic_skipped_for_chitchat():
    """Chitchat intent skips critic entirely."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "chitchat", "entities": {}}
    fake_retriever = MagicMock()
    fake_answerer = MagicMock()
    fake_answerer.answer.return_value = "你好！有什么可以帮你的吗？"
    fake_critic = MagicMock()

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    result = await wf.run(query="你好")

    assert fake_critic.review.call_count == 0
    assert result["answer"] == "你好！有什么可以帮你的吗？"
    assert result["retry_count"] == 0


@pytest.mark.asyncio
async def test_retriever_receives_feedback_in_query():
    """On first retry, the query passed to retriever includes critic feedback."""
    fake_router = MagicMock()
    fake_router.route.return_value = {"intent": "kb_query", "entities": {}}
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = [_chunk()]
    fake_answerer = MagicMock()
    fake_answerer.answer.side_effect = ["bad", "good"]
    fake_critic = MagicMock()
    fake_critic.review.side_effect = [
        {"pass": False, "reason": "幻觉", "suggestion": "请参考官方wiki"},
        {"pass": True, "reason": "ok", "suggestion": ""},
    ]

    wf = McmodWorkflow(
        router=fake_router, retriever=fake_retriever,
        answerer=fake_answerer, critic=fake_critic,
    )
    await wf.run(query="什么是机械动力")

    # The second retrieve call should have the feedback-augmented query
    second_call_query = fake_retriever.retrieve.call_args_list[1].args[0]
    assert "补充信息" in second_call_query
    assert "请参考官方wiki" in second_call_query
    assert "什么是机械动力" in second_call_query
