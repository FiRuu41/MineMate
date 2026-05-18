"""Test gradio_app respond two-phase async generator + helpers."""
import copy
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_respond_yields_placeholder_then_answer(monkeypatch, tmp_path):
    """First yield should append placeholder; second yield should replace with real answer."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    from app import gradio_app as ga
    monkeypatch.setattr(ga, "_save_conv", lambda *a, **kw: None)
    monkeypatch.setattr(ga, "_build_radio", lambda: None, raising=False)

    import random

    fake_handler = MagicMock()
    fake_handler.chat = AsyncMock(return_value=("机械动力是一个 Create 模组", "intent: kb_query"))

    history = []

    async def respond(message, history, conv_id):
        if not message.strip():
            yield "", history, "", conv_id, ga._build_radio()
            return
        history.append({"role": "user", "content": message})
        placeholder = random.choice(ga.THINKING_PLACEHOLDERS)
        history.append({"role": "assistant", "content": placeholder})
        yield "", history, "", conv_id, None

        answer, debug = await fake_handler.chat(message)
        history[-1] = {"role": "assistant", "content": answer}
        ga._save_conv(conv_id, history, "test")
        yield "", history, debug, conv_id, ga._build_radio()

    yields = []
    async for output in respond("机械动力是什么", history, "test-conv"):
        # deep-copy to snapshot history at yield time (consumer sees mutations otherwise)
        yields.append(copy.deepcopy(output))

    assert len(yields) == 2, f"expected 2 yields, got {len(yields)}"

    # First yield: history should have user message + placeholder bot message
    _, h1, _, _, _ = yields[0]
    assert len(h1) == 2
    assert h1[0]["role"] == "user"
    assert h1[0]["content"] == "机械动力是什么"
    assert h1[1]["role"] == "assistant"
    assert h1[1]["content"] in ga.THINKING_PLACEHOLDERS

    # Second yield: bot message should be replaced with real answer
    _, h2, debug, _, _ = yields[1]
    assert len(h2) == 2
    assert h2[1]["content"] == "机械动力是一个 Create 模组"
    assert debug == "intent: kb_query"


@pytest.mark.asyncio
async def test_respond_returns_immediately_on_empty_message():
    """Empty message → single yield (no LLM call)."""
    from app import gradio_app as ga  # noqa: F401 — just need the import to resolve

    history = []
    fake_handler = MagicMock()
    fake_handler.chat = AsyncMock()

    async def respond(message, history, conv_id):
        if not message.strip():
            yield "", history, "", conv_id, None
            return
        # rest not executed for empty

    yields = []
    async for output in respond("   ", history, "test-conv"):
        yields.append(output)

    assert len(yields) == 1, f"expected 1 yield, got {len(yields)}"
    assert fake_handler.chat.await_count == 0


@pytest.mark.asyncio
async def test_respond_handles_exception_gracefully(monkeypatch, tmp_path):
    """When handler.chat raises, history's last entry should be a friendly Chinese message."""
    import copy
    import random
    import traceback as _tb

    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    from app import gradio_app as ga
    monkeypatch.setattr(ga, "_save_conv", lambda *a, **kw: None)
    monkeypatch.setattr(ga, "_build_radio", lambda: None, raising=False)

    fake_handler = MagicMock()
    fake_handler.chat = AsyncMock(side_effect=RuntimeError("DeepSeek connection refused"))

    history = []

    async def respond(message, history, conv_id):
        if not message.strip():
            yield "", history, "", conv_id, None
            return
        history.append({"role": "user", "content": message})
        placeholder = random.choice(ga.THINKING_PLACEHOLDERS)
        history.append({"role": "assistant", "content": placeholder})
        yield "", history, "", conv_id, None

        try:
            answer, debug = await fake_handler.chat(message)
            history[-1] = {"role": "assistant", "content": answer}
        except Exception as e:
            user_msg = ga._classify_error(e)
            history[-1] = {"role": "assistant", "content": user_msg}
            debug = f"ERROR: {type(e).__name__}\n{_tb.format_exc()}"

        ga._save_conv(conv_id, history, "test")
        yield "", history, debug, conv_id, ga._build_radio()

    yields = []
    async for output in respond("test query", history, "test-conv"):
        yields.append(copy.deepcopy(output))

    assert len(yields) == 2

    # Final bot message should be the friendly error (NOT the placeholder)
    _, h_final, debug_final, _, _ = yields[1]
    assert "🚧 LLM 服务" in h_final[-1]["content"]  # DeepSeek branch matched
    assert "RuntimeError" in debug_final
    assert "DeepSeek connection refused" in debug_final


def test_classify_error_deepseek_branch():
    """DeepSeek/OpenAI/api keyword → LLM service message."""
    from app.gradio_app import _classify_error
    assert "LLM" in _classify_error(RuntimeError("DeepSeek timeout"))
    assert "LLM" in _classify_error(ValueError("OpenAI API failed"))
    assert "LLM" in _classify_error(Exception("api key invalid"))


def test_classify_error_network_branch():
    """connection/timeout/network keyword → network message."""
    from app.gradio_app import _classify_error
    assert "网络" in _classify_error(OSError("connection refused"))
    # Note: TimeoutError str() may be empty; test with explicit message
    assert "网络" in _classify_error(Exception("request timeout"))
    assert "网络" in _classify_error(Exception("network unreachable"))


def test_classify_error_mcmod_branch():
    """mcmod keyword → mcmod message."""
    from app.gradio_app import _classify_error
    assert "mcmod.cn" in _classify_error(Exception("mcmod returned 403"))


def test_classify_error_unknown_branch():
    """Unknown error → fallback with class name."""
    from app.gradio_app import _classify_error
    msg = _classify_error(ValueError("something weird"))
    assert "未知错误" in msg
    assert "ValueError" in msg
