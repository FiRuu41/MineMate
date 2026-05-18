from unittest.mock import MagicMock

from llm.deepseek_client import DeepSeekClient


def test_chat_returns_content():
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="hi"))]
    fake_client.chat.completions.create.return_value = fake_resp
    c = DeepSeekClient(client=fake_client)
    assert c.chat([{"role": "user", "content": "hello"}]) == "hi"


def test_chat_json_mode():
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"a": 1}'))]
    fake_client.chat.completions.create.return_value = fake_resp
    c = DeepSeekClient(client=fake_client)
    out = c.chat_json([{"role": "user", "content": "x"}])
    assert out == {"a": 1}


def test_chat_json_strips_markdown_fence():
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='```json\n{"a": 2}\n```'))]
    fake_client.chat.completions.create.return_value = fake_resp
    c = DeepSeekClient(client=fake_client)
    assert c.chat_json([{"role": "user", "content": "x"}]) == {"a": 2}


def test_chat_json_invalid_returns_empty():
    fake_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"broken: 1'))]
    fake_client.chat.completions.create.return_value = fake_resp
    c = DeepSeekClient(client=fake_client)
    # Invalid JSON should return {} instead of raising
    assert c.chat_json([{"role": "user", "content": "x"}]) == {}
