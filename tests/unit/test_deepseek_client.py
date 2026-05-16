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
