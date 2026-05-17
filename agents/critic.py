"""Critic Agent: validate answer quality and detect hallucinations."""
from pathlib import Path

from loguru import logger

from llm.deepseek_client import DeepSeekClient

PROMPT_PATH = Path("config/prompts/critic.txt")


class CriticAgent:
    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self.llm = llm or DeepSeekClient()
        self._template = PROMPT_PATH.read_text(encoding="utf-8")

    def review(self, question: str, answer: str, context: str) -> dict:
        prompt = self._template.format(question=question, answer=answer, context=context)
        try:
            result = self.llm.chat_json([{"role": "user", "content": prompt}], temperature=0.0)
        except Exception as e:
            logger.warning("critic llm failed, default pass: {}", e)
            return {"pass": True, "reason": "critic unavailable", "suggestion": ""}
        return {
            "pass": bool(result.get("pass", True)),
            "reason": result.get("reason", ""),
            "suggestion": result.get("suggestion", ""),
        }
