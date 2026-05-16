from unittest.mock import MagicMock

from agents.router import RouterAgent


def test_router_kb_query():
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {"intent": "kb_query", "entities": {"mod_name": "机械动力"}}
    r = RouterAgent(llm=fake_llm)
    out = r.route("机械动力的动力源有哪些？")
    assert out["intent"] == "kb_query"
    assert out["entities"]["mod_name"] == "机械动力"


def test_router_unknown_defaults_to_kb():
    fake_llm = MagicMock()
    fake_llm.chat_json.return_value = {"intent": "weird", "entities": {}}
    r = RouterAgent(llm=fake_llm)
    out = r.route("???")
    assert out["intent"] == "kb_query"


def test_router_llm_error_defaults():
    fake_llm = MagicMock()
    fake_llm.chat_json.side_effect = ValueError("bad json")
    r = RouterAgent(llm=fake_llm)
    out = r.route("xx")
    assert out["intent"] == "kb_query"
