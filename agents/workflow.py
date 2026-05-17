from loguru import logger

from kb.schemas import Chunk
from config.settings import settings


import random

STATUS_MSGS = {
    "routing": [
        "🤔 正在理解你的问题...",
        "🔍 分析问题中...",
        "💭 思考中...",
    ],
    "retrieving": [
        "📚 正在翻书中...",
        "🔎 搜索模组百科中...",
        "📖 翻阅知识库...",
        "🏗️ 挖掘信息中...",
        "⛏️ 正在开采数据...",
    ],
    "answering": [
        "✍️ 正在整理回答...",
        "📝 撰写回复中...",
        "💡 组织信息中...",
    ],
    "web_fallback": [
        "🌐 正在查询网页，请稍后...",
        "🕸️ 联网搜索中...",
        "🌍 翻阅在线百科...",
    ],
    "recommend": [
        "🎯 正在搜索模组...",
        "🔮 寻找匹配的模组...",
        "🧭 探索模组世界...",
    ],
    "compat": [
        "🔗 检查兼容性中...",
        "🔄 分析模组关系...",
    ],
    "modpack": [
        "📦 正在编排整合包...",
        "🎒 打包模组中...",
        "🗂️ 整理模组列表...",
    ],
    "info": [
        "📋 查询模组信息...",
        "🔎 查找资料中...",
    ],
}


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

    def _status(self, key: str) -> str:
        return random.choice(STATUS_MSGS.get(key, ["⏳ 处理中..."]))

    async def run(self, *, query: str, chat_history: str = "", exclude_ids: list[str] | None = None) -> dict:
        status = self._status("routing")
        routing = self.router.route(query, chat_history=chat_history)
        intent = routing["intent"]
        entities = routing["entities"]

        chunks: list[Chunk] = []
        tool_results: dict = {}
        retry_count = 0
        original_query = query

        if intent == "kb_query":
            status = self._status("retrieving")
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

            # Auto web fallback: if answer says "not found", try real-time search
            if "未在知识库" in answer or "未找到" in answer:
                status = self._status("web_fallback")
                from tools.web_search_mcmod import web_search_mcmod
                logger.info("kb_query not found, trying web fallback")
                # First: if we know the mod, go directly to its mcmod page
                mod_name = entities.get("mod_name", "")
                if isinstance(mod_name, list):
                    mod_name = mod_name[0] if mod_name else ""
                mod_id = self._entity_to_mod_id(mod_name)
                web_context = ""
                if mod_id:
                    # Fetch the mod's page directly from MySQL URL
                    from pipeline.storage.db import SessionLocal
                    from pipeline.storage.models import Mod
                    with SessionLocal() as s:
                        m = s.get(Mod, mod_id)
                        if m and m.mcmod_url:
                            from tools.web_search_mcmod import fetch_page, parse_page_intro
                            logger.info("Fetching mod page directly: {}", m.mcmod_url)
                            html = fetch_page(m.mcmod_url)
                            if html:
                                web_context = parse_page_intro(html)
                                logger.info("Fetched page: {} chars", len(web_context))
                # Fallback: keyword search
                if not web_context:
                    short_q = (mod_name + " " + original_query[:30]).strip() if mod_name else original_query[:40]
                    logger.info("Direct fetch failed, trying search: {}", short_q)
                    web_results = web_search_mcmod(short_q, top_k=2, fetch_pages=True)
                    if web_results and "error" not in web_results[0]:
                        web_context = "\n\n".join(
                            r.get("page_content", r.get("snippet", ""))
                            for r in web_results if "error" not in r
                        )
                if web_context:
                    from kb.schemas import Chunk, ChunkMetadata
                    page_url = ""
                    if mod_id:
                        try:
                            page_url = m.mcmod_url or ""
                        except NameError:
                            page_url = ""
                    fake_md = ChunkMetadata(mod_id=mod_id or "web", mod_name_zh="在线获取", section="web",
                                             source_url=page_url or "https://www.mcmod.cn", title="在线获取")
                    chunks = [Chunk(text=web_context[:3000], metadata=fake_md, score=1.0)]
                    answer = self.answerer.answer(original_query, chunks, {"web_results": [{"url": url}]})

        elif intent == "mod_info_query":
            status = self._status("info")
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
            tool_results["latest_mods"] = find_latest_mods(tags=tags or None, mc_version=mc_ver, top_k=15)
            answer = self.answerer.answer(query, chunks, tool_results)

        elif intent == "modpack_curation":
            status = self._status("modpack")
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
            status = self._status("recommend")
            from tools.recommend_mods import recommend_mods
            tags = entities.get("tags", [])
            tool_results["recommendations"] = recommend_mods(tags=tags, top_k=15, exclude_ids=exclude_ids)
            answer = self.answerer.answer(query, chunks, tool_results)
        elif intent == "compatibility":
            status = self._status("compat")
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

        # Done — show answering status
        status = self._status("answering")
        return {
            "intent": intent, "answer": answer, "chunks": chunks,
            "tool_results": tool_results, "retry_count": retry_count, "status": status,
        }

    @staticmethod
    def _entity_to_mod_id(mod_name) -> str | None:
        # Router may return a list for multi-mod queries
        if isinstance(mod_name, list):
            mod_name = mod_name[0] if mod_name else None
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
