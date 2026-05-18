"""Tests for CriticAgent with mocked LLM."""
from unittest.mock import MagicMock

from agents.critic import CriticAgent


def test_critic_passes():
    """Critic returns pass=True when answer is valid."""
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {"pass": True, "reason": "回答正确", "suggestion": ""}
    critic = CriticAgent(llm=fake_llm)
    result = critic.review(
        "什么是机械动力", "机械动力是一个工程模组", "参考资料：机械动力是工程模组",
    )
    assert result["pass"] is True
    assert result["reason"] == "回答正确"
    assert result["suggestion"] == ""


def test_critic_fails():
    """Critic returns pass=False when answer has issues."""
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {
        "pass": False, "reason": "存在幻觉", "suggestion": "请基于参考资料回答",
    }
    critic = CriticAgent(llm=fake_llm)
    result = critic.review(
        "什么是机械动力", "机械动力是一个魔法模组", "参考资料：机械动力是工程模组",
    )
    assert result["pass"] is False
    assert result["reason"] == "存在幻觉"
    assert result["suggestion"] == "请基于参考资料回答"


def test_critic_llm_error_fallback():
    """When LLM call fails, critic defaults to pass=True."""
    fake_llm = MagicMock()
    fake_llm.chat_json.side_effect = RuntimeError("connection lost")
    critic = CriticAgent(llm=fake_llm)
    result = critic.review("q", "a", "ctx")
    assert result["pass"] is True
    assert result["reason"] == "critic unavailable"
    assert result["suggestion"] == ""


def test_critic_default_llm_construction():
    """CriticAgent can be constructed with default LLM (uses env vars from conftest)."""
    critic = CriticAgent()
    assert critic._template is not None
    assert "question" in critic._template
    assert "answer" in critic._template
    assert "context" in critic._template


def test_critic_prompt_contains_inputs():
    """Verify that the prompt template is populated with question, answer, and context."""
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {"pass": True, "reason": "ok", "suggestion": ""}
    critic = CriticAgent(llm=fake_llm)
    critic.review("问题A", "回答B", "上下文C")
    call_args = fake_llm.chat_json.call_args.args[0]
    user_content = call_args[0]["content"]
    assert "问题A" in user_content
    assert "回答B" in user_content
    assert "上下文C" in user_content


def test_critic_defaults_to_true_when_pass_missing():
    """When LLM returns JSON without 'pass' key, default to True."""
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {"reason": "missing pass key"}
    critic = CriticAgent(llm=fake_llm)
    result = critic.review("q", "a", "ctx")
    assert result["pass"] is True
    assert result["reason"] == "missing pass key"
