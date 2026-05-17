from kb.schemas import Chunk

from config.settings import settings


class McmodWorkflow:
    """Serial MVP workflow (router -> retriever/tools -> answerer)."""

    def __init__(self, router, retriever, answerer) -> None:
        self.router = router
        self.retriever = retriever
        self.answerer = answerer

    async def run(self, *, query: str) -> dict:
        routing = self.router.route(query)
        intent = routing["intent"]
        entities = routing["entities"]

        chunks: list[Chunk] = []
        tool_results: dict = {}

        if intent == "kb_query":
            mod_id = self._entity_to_mod_id(entities.get("mod_name"))
            chunks = self.retriever.retrieve(query, top_k=settings.top_k, mod_id=mod_id)
        elif intent == "recommendation":
            from tools.recommend_mods import recommend_mods
            tags = entities.get("tags", [])
            tool_results["recommendations"] = recommend_mods(tags=tags, top_k=5)
        elif intent == "compatibility":
            from tools.compatibility import get_compatible_mods
            mod_name = entities.get("mod_name")
            mod_id = self._entity_to_mod_id(mod_name)
            if mod_id:
                tool_results["compatible_mods"] = get_compatible_mods(mod_id)
            else:
                tool_results["compatible_mods"] = []

        answer = self.answerer.answer(query, chunks, tool_results)
        return {"intent": intent, "answer": answer, "chunks": chunks, "tool_results": tool_results}

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
