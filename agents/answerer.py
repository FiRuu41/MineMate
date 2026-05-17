from pathlib import Path

from kb.schemas import Chunk
from llm.deepseek_client import DeepSeekClient

PROMPT_PATH = Path("config/prompts/answerer.txt")


class AnswererAgent:
    def __init__(self, llm: DeepSeekClient | None = None) -> None:
        self.llm = llm or DeepSeekClient()
        self._template = PROMPT_PATH.read_text(encoding="utf-8")

    def _format_context(self, chunks: list[Chunk], tool_results: dict) -> str:
        parts = []
        if chunks:
            lines = []
            for i, c in enumerate(chunks, start=1):
                lines.append(
                    f"[来源{i}] {c.metadata.mod_name_zh}"
                    f"（{c.metadata.section}, {c.metadata.source_url}）\n{c.text}"
                )
            parts.append("\n\n".join(lines))
        if tool_results.get("recommendations"):
            recs = tool_results["recommendations"]
            lines = ["### 推荐模组"]
            for r in recs:
                tags_str = ", ".join(r.get("tags", {}).get("genres", []))
                lines.append(f"- **{r['name_zh']}** ({r.get('name_en', '')}) — {tags_str} — {r['mcmod_url']}")
            parts.append("\n".join(lines))
        if tool_results.get("compatible_mods"):
            comps = tool_results["compatible_mods"]
            lines = ["### 兼容模组"]
            for c in comps:
                ver = ", ".join(c.get("common_mc_versions", []))
                lines.append(
                    f"- **{c['mod_name_zh']}** — 共同版本: {ver or '未知'} — "
                    f"{c.get('evidence', '')}"
                )
            parts.append("\n".join(lines))
        return "\n\n".join(parts) if parts else "（无可用资料）"

    def answer(self, question: str, chunks: list[Chunk], tool_results: dict | None = None) -> str:
        ctx = self._format_context(chunks, tool_results or {})
        prompt = self._template.format(context=ctx, question=question)
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.3)
