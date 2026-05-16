from pathlib import Path

from kb.schemas import Chunk
from llm.deepseek_client import DeepSeekClient

PROMPT_PATH = Path("config/prompts/answerer.txt")


class AnswererAgent:
    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self.llm = llm or DeepSeekClient()
        self._template = PROMPT_PATH.read_text(encoding="utf-8")

    def _format_context(self, chunks: list[Chunk]) -> str:
        if not chunks:
            return "（无可用资料）"
        lines = []
        for i, c in enumerate(chunks, start=1):
            lines.append(f"[来源{i}] {c.metadata.mod_name_zh}（{c.metadata.section}, {c.metadata.source_url}）\n{c.text}")
        return "\n\n".join(lines)

    def answer(self, question: str, chunks: list[Chunk]) -> str:
        prompt = self._template.format(context=self._format_context(chunks), question=question)
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.3)
