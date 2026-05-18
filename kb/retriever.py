"""Hybrid retriever: ChromaDB vector search + SQLite LIKE keyword search, merged via RRF."""
import re

from kb.schemas import Chunk, ChunkMetadata


class HybridRetriever:
    """Vector search + keyword match, merged via Reciprocal Rank Fusion."""

    def __init__(self, vector_retriever=None) -> None:
        if vector_retriever is not None:
            self.vector = vector_retriever
        else:
            from kb.chroma_retriever import ChromaRetriever
            self.vector = ChromaRetriever()

    def retrieve(self, query: str, top_k: int = 8, mod_id: str | None = None,
                 section: str | None = None) -> list[Chunk]:
        vec_results = self.vector.retrieve(query, top_k=top_k * 2,
                                            mod_id=mod_id, section=section)
        kw_results = self._keyword_search(query, top_k=top_k, mod_id=mod_id)
        return self._rrf_merge(vec_results, kw_results, k=60, top_k=top_k)

    def _keyword_search(self, query: str, top_k: int = 8,
                        mod_id: str | None = None) -> list[Chunk]:
        """SQLite LIKE-based keyword fallback. Searches Mod.description for
        Chinese tokens and English words >= 3 chars, ordered by description length."""
        keywords = re.findall(r'[一-鿿]+|[a-zA-Z]{3,}', query)[:5]
        if not keywords:
            return []

        from sqlalchemy import func, or_

        from pipeline.storage.db import SessionLocal
        from pipeline.storage.models import Mod

        try:
            with SessionLocal() as s:
                conds = [Mod.description.contains(kw) for kw in keywords]
                q = s.query(Mod).filter(or_(*conds))
                if mod_id:
                    q = q.filter(Mod.mod_id == mod_id)
                rows = q.order_by(func.length(Mod.description).desc()).limit(top_k).all()
                return [self._mod_to_chunk(m) for m in rows]
        except Exception:
            return []

    def _mod_to_chunk(self, m) -> Chunk:
        md = ChunkMetadata(
            mod_id=m.mod_id,
            mod_name_zh=m.name_zh,
            section="intro",
            source_url=m.mcmod_url,
            title=f"{m.name_zh} 简介",
        )
        return Chunk(text=(m.description or "")[:2000], metadata=md, score=0.5)

    @staticmethod
    def _rrf_merge(vec: list[Chunk], kw: list[Chunk], k: int = 60,
                   top_k: int = 8) -> list[Chunk]:
        """Reciprocal Rank Fusion: merge two ranked lists."""
        scores: dict[str, tuple[float, Chunk]] = {}

        for rank, c in enumerate(vec):
            key = c.metadata.source_url + c.text[:100]
            rrf = 1.0 / (k + rank + 1)
            if key in scores:
                scores[key] = (scores[key][0] + rrf, c)
            else:
                scores[key] = (rrf, c)

        for rank, c in enumerate(kw):
            key = c.metadata.source_url + c.text[:100]
            rrf = 1.0 / (k + rank + 1)
            if key in scores:
                scores[key] = (scores[key][0] + rrf, c)
            else:
                scores[key] = (rrf, c)

        sorted_items = sorted(scores.values(), key=lambda x: -x[0])
        result = [c for _, c in sorted_items[:top_k]]
        for c in result:
            key = c.metadata.source_url + c.text[:100]
            c.score = scores.get(key, (0, c))[0]
        return result
