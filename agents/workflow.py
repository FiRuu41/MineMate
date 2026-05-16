from kb.schemas import Chunk

from config.settings import settings


class McmodWorkflow:
    """Serial MVP workflow (router -> retriever -> answerer).

    Stage 2 will migrate to llama_index.core.workflow.Workflow with Event-driven graph.
    """

    def __init__(self, router, retriever, answerer) -> None:
        self.router = router
        self.retriever = retriever
        self.answerer = answerer

    async def run(self, *, query: str) -> dict:
        routing = self.router.route(query)
        intent = routing["intent"]
        entities = routing["entities"]

        chunks: list[Chunk] = []
        if intent == "kb_query":
            mod_id = self._entity_to_mod_id(entities.get("mod_name"))
            chunks = self.retriever.retrieve(query, top_k=settings.top_k, mod_id=mod_id)

        answer = self.answerer.answer(query, chunks)
        return {"intent": intent, "answer": answer, "chunks": chunks}

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
