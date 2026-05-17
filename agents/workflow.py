from kb.schemas import Chunk

from config.settings import settings


class McmodWorkflow:
    """MVP workflow with multi-turn memory support and critic retry loop."""

    def __init__(self, router, retriever, answerer, critic=None) -> None:
        self.router = router
        self.retriever = retriever
        self.answerer = answerer
        if critic is None:
            from agents.critic import CriticAgent
            critic = CriticAgent()
        self.critic = critic

    async def run(self, *, query: str, chat_history: str = "") -> dict:
        routing = self.router.route(query, chat_history=chat_history)
        intent = routing["intent"]
        entities = routing["entities"]

        chunks: list[Chunk] = []
        tool_results: dict = {}
        retry_count = 0
        original_query = query

        if intent == "kb_query":
            mod_id = self._entity_to_mod_id(entities.get("mod_name"))
            chunks = self.retriever.retrieve(query, top_k=settings.top_k, mod_id=mod_id)

            for retry in range(3):  # 0, 1, 2 — max 2 retries
                answer = self.answerer.answer(query, chunks, tool_results)
                context = self._chunks_to_context(chunks)
                review = self.critic.review(original_query, answer, context)

                if review["pass"]:
                    retry_count = retry
                    break

                # Max 2 retries exhausted — keep last answer
                if retry == 2:
                    retry_count = retry
                    break

                # Rewrite query with critic feedback and re-retrieve
                query = f"{original_query}（补充信息：{review['suggestion']}）"
                chunks = self.retriever.retrieve(query, top_k=settings.top_k * (retry + 2), mod_id=mod_id)

            # If final review still failed, prefix warning
            if not review.get("pass"):
                answer = "⚠️ 此回答未通过自动校验，仅供参考\n\n" + answer

        elif intent == "mod_info_query":
            from tools.get_mod_info import get_mod_info
            mod_name = entities.get("mod_name")
            mod_id = self._entity_to_mod_id(mod_name)
            if mod_id or mod_name:
                tool_results["mod_info"] = get_mod_info(mod_id or mod_name)
            else:
                tool_results["mod_info"] = {"error": "no mod name extracted"}
            answer = self.answerer.answer(query, chunks, tool_results)

        elif intent == "web_fallback":
            from tools.web_search_mcmod import web_search_mcmod
            tool_results["web_results"] = web_search_mcmod(query, top_k=5)
            answer = self.answerer.answer(query, chunks, tool_results)

        elif intent == "latest_mods":
            from tools.find_latest_mods import find_latest_mods
            tags = entities.get("tags", [])
            mc_ver = entities.get("mc_version")
            tool_results["latest_mods"] = find_latest_mods(tags=tags or None, mc_version=mc_ver, top_k=10)
            answer = self.answerer.answer(query, chunks, tool_results)

        elif intent == "modpack_curation":
            from tools.curate_modpack import curate_modpack
            tags = entities.get("tags", [])
            mc_ver = entities.get("mc_version")
            pref = entities.get("preference", "")
            loader = entities.get("loader")
            tool_results["modpack"] = curate_modpack(
                themes=tags, mc_version=mc_ver, loader=loader, preference=pref, max_mods=15,
            )
            answer = self.answerer.answer(query, chunks, tool_results)

        elif intent == "recommendation":
            from tools.recommend_mods import recommend_mods
            tags = entities.get("tags", [])
            tool_results["recommendations"] = recommend_mods(tags=tags, top_k=5)
            answer = self.answerer.answer(query, chunks, tool_results)
        elif intent == "compatibility":
            from tools.compatibility import get_compatible_mods
            mod_name = entities.get("mod_name")
            mod_id = self._entity_to_mod_id(mod_name)
            if mod_id:
                tool_results["compatible_mods"] = get_compatible_mods(mod_id)
            else:
                tool_results["compatible_mods"] = []
            answer = self.answerer.answer(query, chunks, tool_results)
        else:
            answer = self.answerer.answer(query, chunks, tool_results)

        return {
            "intent": intent, "answer": answer, "chunks": chunks,
            "tool_results": tool_results, "retry_count": retry_count,
        }

    @staticmethod
    def _entity_to_mod_id(mod_name: str | None) -> str | None:
        if not mod_name:
            return None
        mapping = {
            "投影": "litematica", "Litematica": "litematica",
            "机械动力": "create", "Create": "create",
            "JEI": "jei", "JEI物品管理": "jei",
            "植物魔法": "botania", "Botania": "botania",
        }
        return mapping.get(mod_name)

    @staticmethod
    def _chunks_to_context(chunks: list[Chunk]) -> str:
        """Format chunks into a reference string for the critic."""
        if not chunks:
            return "（无可用资料）"
        lines = []
        for i, c in enumerate(chunks, start=1):
            lines.append(
                f"[来源{i}] {c.metadata.mod_name_zh}"
                f"（{c.metadata.section}, {c.metadata.source_url}）\n{c.text}"
            )
        return "\n\n".join(lines)
