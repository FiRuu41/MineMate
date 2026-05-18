from loguru import logger

from kb.retriever import HybridRetriever


def search_mcmod_kb_with(retriever: HybridRetriever, *, query: str, mod_id: str | None = None,
                         section: str | None = None, top_k: int = 8) -> list[dict] | dict:
    try:
        chunks = retriever.retrieve(query, top_k=top_k, mod_id=mod_id, section=section)
    except Exception as e:
        logger.exception("search_mcmod_kb failed")
        return {"error": str(e)}
    return [
        {
            "text": c.text,
            "score": c.score,
            "mod_id": c.metadata.mod_id,
            "mod_name_zh": c.metadata.mod_name_zh,
            "section": c.metadata.section,
            "mc_version": c.metadata.mc_version,
            "source_url": c.metadata.source_url,
            "title": c.metadata.title,
        }
        for c in chunks
    ]


_DEFAULT_RETRIEVER: HybridRetriever | None = None


def search_mcmod_kb(
    query: str, mod_id: str | None = None,
    section: str | None = None, top_k: int = 8,
):
    """Default-retriever convenience wrapper for LlamaIndex FunctionTool."""
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = HybridRetriever()
    return search_mcmod_kb_with(
        _DEFAULT_RETRIEVER, query=query, mod_id=mod_id, section=section, top_k=top_k,
    )
