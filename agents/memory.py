"""Simple conversation memory buffer."""


class ConversationMemory:
    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self._messages: list[dict] = []

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})

    def get_history(self, last_n: int | None = None) -> list[dict]:
        n = last_n or self.max_turns * 2
        return self._messages[-n:]

    def clear(self) -> None:
        self._messages = []

    def format_for_prompt(self, last_n: int = 6) -> str:
        """Format recent history as a readable string for prompts."""
        recent = self._messages[-last_n * 2:]
        if not recent:
            return ""
        lines = ["## 对话历史"]
        for m in recent:
            role = "用户" if m["role"] == "user" else "助手"
            content = m["content"][:500]
            lines.append(f"{role}：{content}")
        return "\n".join(lines)
