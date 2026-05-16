from llama_index.core.workflow import Event

from kb.schemas import Chunk


class RouterDoneEvent(Event):
    intent: str
    entities: dict
    user_query: str


class RetrieveDoneEvent(Event):
    chunks: list[Chunk]
    user_query: str
    intent: str


class AnswerReadyEvent(Event):
    answer: str
    chunks: list[Chunk]
    intent: str
