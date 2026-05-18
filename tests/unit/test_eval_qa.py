"""Smoke tests for scripts.eval_qa helpers."""
from scripts.eval_qa import _judge, _keyword_hit_rate


def test_keyword_hit_rate_empty_keywords():
    """No keywords expected → 1.0 (vacuously pass)."""
    assert _keyword_hit_rate("anything", []) == 1.0


def test_keyword_hit_rate_partial():
    """2 of 4 keywords appear in text → 0.5."""
    text = "机械动力是一个 Create 模组，主要是机械"
    keywords = ["机械动力", "Create", "齿轮", "活塞"]
    assert _keyword_hit_rate(text, keywords) == 0.5


def test_keyword_hit_rate_full():
    """All keywords present → 1.0."""
    text = "机械动力 (Create) 是 Forge 模组"
    keywords = ["机械动力", "Create", "Forge"]
    assert _keyword_hit_rate(text, keywords) == 1.0


def test_judge_passes_intent_match_and_keywords():
    """intent matches + 70%+ keywords → passed=True."""
    result = {
        "intent": "kb_query",
        "answer": "机械动力 (Create) 是热门科技模组",
    }
    expected = {
        "query": "机械动力是什么",
        "expected_intent": "kb_query",
        "expected_keywords": ["机械动力", "Create"],
    }
    verdict = _judge(result, expected)
    assert verdict["passed"] is True
    assert verdict["intent_match"] is True
    assert verdict["hit_rate"] == 1.0


def test_judge_fails_when_intent_mismatch():
    """intent mismatch → passed=False even if keywords all hit."""
    result = {
        "intent": "recommendation",
        "answer": "机械动力 (Create)",
    }
    expected = {
        "query": "机械动力是什么",
        "expected_intent": "kb_query",
        "expected_keywords": ["机械动力", "Create"],
    }
    verdict = _judge(result, expected)
    assert verdict["passed"] is False
    assert verdict["intent_match"] is False


def test_judge_fails_when_hit_rate_below_threshold():
    """hit_rate < 70% → passed=False."""
    result = {
        "intent": "kb_query",
        "answer": "机械动力",  # Only 1 of 3 keywords
    }
    expected = {
        "query": "机械动力是什么",
        "expected_intent": "kb_query",
        "expected_keywords": ["机械动力", "Create", "Forge"],  # 1/3 = 33%
    }
    verdict = _judge(result, expected)
    assert verdict["passed"] is False
    assert verdict["intent_match"] is True
    assert verdict["hit_rate"] < 0.7
