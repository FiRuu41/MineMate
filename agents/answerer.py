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
        if tool_results.get("latest_mods"):
            latest = tool_results["latest_mods"]
            lines = ["### 最新模组"]
            for m in latest:
                tags_str = ", ".join((m.get("tags") or {}).get("genres", []))
                ver = (m.get("mc_versions") or [None])[0]
                lines.append(f"- **{m['name_zh']}** ({m.get('name_en', '')}) — {tags_str} — MC {ver} — {m['mcmod_url']}")
            parts.append("\n".join(lines))
        if tool_results.get("modpack"):
            mp = tool_results["modpack"]
            lines = [f"### 整合包推荐 — {mp.get('theme', '')}"]
            if mp.get("mc_version"):
                lines.append(f"MC 版本: {mp['mc_version']}")
            if mp.get("preference"):
                lines.append(f"风格: {mp['preference']}")
            for cat, mods in mp.get("categories", {}).items():
                lines.append(f"\n**{cat}** ({len(mods)} 个)")
                for m in mods:
                    tags_str = ", ".join((m.get("tags") or {}).get("genres", []))
                    ver = (m.get("mc_versions") or [None])[0]
                    lines.append(f"- {m['name_zh']} ({m.get('name_en', '')}) — {tags_str} — MC {ver}")
            if mp.get("compatibility_notes"):
                lines.append("\n**兼容性提示:**")
                for note in mp["compatibility_notes"]:
                    lines.append(f"- {note}")
            if mp.get("disclaimer"):
                lines.append(f"\n> {mp['disclaimer']}")
            parts.append("\n".join(lines))
        if tool_results.get("mod_info"):
            mi = tool_results["mod_info"]
            if "error" not in mi:
                lines = ["### 模组信息"]
                lines.append(f"- 名称: {mi.get('name_zh', '')} ({mi.get('name_en', '')})")
                if mi.get("loader"):
                    lines.append(f"- Loader: {mi['loader']}")
                if mi.get("mc_versions"):
                    lines.append(f"- MC 版本: {', '.join(mi['mc_versions'])}")
                if mi.get("author"):
                    lines.append(f"- 作者: {mi['author']}")
                if mi.get("description"):
                    lines.append(f"- 简介: {mi['description'][:500]}")
                lines.append(f"- 链接: {mi.get('mcmod_url', '')}")
                parts.append("\n".join(lines))
        return "\n\n".join(parts) if parts else "（无可用资料）"

    def answer(self, question: str, chunks: list[Chunk], tool_results: dict | None = None) -> str:
        ctx = self._format_context(chunks, tool_results or {})
        prompt = self._template.format(context=ctx, question=question)
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.3)
