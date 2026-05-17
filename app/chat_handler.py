from loguru import logger

from agents.memory import ConversationMemory
from agents.workflow import McmodWorkflow
from config.logging import new_trace_id


class ChatHandler:
    def __init__(self, workflow: McmodWorkflow) -> None:
        self.workflow = workflow
        self.memory = ConversationMemory()

    async def chat(self, message: str) -> tuple[str, str]:
        new_trace_id()
        logger.info("user> {}", message)
        self.memory.add_user(message)
        history = self.memory.format_for_prompt()
        result = await self.workflow.run(query=message, chat_history=history)
        self.memory.add_assistant(result["answer"])
        debug = self._format_debug(result)
        logger.info("intent={}, chunks={}", result["intent"], len(result["chunks"]))
        return result["answer"], debug

    def get_history(self) -> list[dict]:
        """Return all messages for chatbot display."""
        return self.memory.get_history()

    def clear(self) -> None:
        self.memory.clear()

    @staticmethod
    def _format_debug(result: dict) -> str:
        lines = [f"intent: {result['intent']}", f"retrieved: {len(result['chunks'])}"]
        for i, c in enumerate(result["chunks"], start=1):
            score = c.score if c.score is not None else 0.0
            lines.append(f"[{i}] score={score:.3f} {c.metadata.mod_name_zh} - {c.metadata.title}")
        if result.get("tool_results", {}).get("recommendations"):
            n = len(result["tool_results"]["recommendations"])
            lines.append(f"recommendations: {n} mods")
        if result.get("tool_results", {}).get("compatible_mods"):
            n = len(result["tool_results"]["compatible_mods"])
            lines.append(f"compatible_mods: {n} entries")
        return "\n".join(lines)
