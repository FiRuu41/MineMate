from loguru import logger

from agents.workflow import McmodWorkflow
from config.logging import new_trace_id


class ChatHandler:
    def __init__(self, workflow: McmodWorkflow) -> None:
        self.workflow = workflow

    async def chat(self, message: str) -> tuple[str, str]:
        new_trace_id()
        logger.info("user> {}", message)
        result = await self.workflow.run(query=message)
        debug = self._format_debug(result)
        logger.info("intent={}, chunks={}", result["intent"], len(result["chunks"]))
        return result["answer"], debug

    @staticmethod
    def _format_debug(result: dict) -> str:
        lines = [f"intent: {result['intent']}", f"retrieved: {len(result['chunks'])}"]
        for i, c in enumerate(result["chunks"], start=1):
            score = c.score if c.score is not None else 0.0
            lines.append(f"[{i}] score={score:.3f} {c.metadata.mod_name_zh} - {c.metadata.title}")
        return "\n".join(lines)
