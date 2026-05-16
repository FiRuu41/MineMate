from unittest.mock import MagicMock

from agents.answerer import AnswererAgent
from kb.schemas import Chunk, ChunkMetadata


def _chunk(mod_id="create", text="机械动力是一个工程模组。"):
    md = ChunkMetadata(
        mod_id=mod_id, mod_name_zh="机械动力", section="intro",
        mc_version="1.20.1", source_url="u", title="t",
    )
    return Chunk(text=text, metadata=md, score=0.9)


def test_answer_uses_chunks():
    fake_llm = MagicMock()
    fake_llm.chat.return_value = "机械动力是一个工程模组 [来源1]。"
    a = AnswererAgent(llm=fake_llm)
    out = a.answer("什么是机械动力", [_chunk()])
    assert "[来源1]" in out
    msgs = fake_llm.chat.call_args.args[0]
    user_msg = msgs[-1]["content"]
    assert "机械动力是一个工程模组" in user_msg


def test_answer_no_chunks_chitchat():
    fake_llm = MagicMock()
    fake_llm.chat.return_value = "你好！"
    a = AnswererAgent(llm=fake_llm)
    out = a.answer("你好", [])
    assert out == "你好！"
