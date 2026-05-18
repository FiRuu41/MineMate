from pathlib import Path

from loguru import logger

from llm.deepseek_client import DeepSeekClient

PROMPT_PATH = Path("config/prompts/router.txt")
VALID_INTENTS = {
    "kb_query", "chitchat", "recommendation", "compatibility",
    "mod_info_query", "web_fallback", "latest_mods", "modpack_curation",
}


class RouterAgent:
    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self.llm = llm or DeepSeekClient()
        self._system = PROMPT_PATH.read_text(encoding="utf-8")

    def route(self, user_query: str, chat_history: str = "") -> dict:
        system_msg = self._system
        if chat_history:
            system_msg += f"\n\n{chat_history}"
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_query},
        ]
        try:
            out = self.llm.chat_json(messages)
        except Exception as e:
            logger.warning("router llm failed, default kb_query: {}", e)
            return {"intent": "kb_query", "entities": {}}
        intent = out.get("intent")
        if intent not in VALID_INTENTS:
            intent = "kb_query"
        return {"intent": intent, "entities": out.get("entities") or {}}
