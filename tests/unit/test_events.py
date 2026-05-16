from agents.events import AnswerReadyEvent, RetrieveDoneEvent, RouterDoneEvent
from kb.schemas import Chunk, ChunkMetadata


def test_events_construct():
    e1 = RouterDoneEvent(intent="kb_query", entities={}, user_query="q")
    md = ChunkMetadata(mod_id="x", mod_name_zh="x", section="intro", source_url="u", title="t")
    e2 = RetrieveDoneEvent(chunks=[Chunk(text="a", metadata=md)], user_query="q", intent="kb_query")
    e3 = AnswerReadyEvent(answer="a", chunks=[], intent="kb_query")
    assert e1.intent == "kb_query"
    assert e2.chunks[0].text == "a"
    assert e3.answer == "a"
