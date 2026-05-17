import re
from collections import OrderedDict

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config.settings import settings
from kb.schemas import Chunk, ChunkMetadata
from llm.embeddings import get_embedder


class VectorRetriever:
    def __init__(self, client: QdrantClient | None = None, embedder=None, collection: str | None = None) -> None:
        self.client = client or QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self.embedder = embedder or get_embedder()
        self.collection = collection or settings.qdrant_collection

    def retrieve(self, query: str, top_k: int = 8, mod_id: str | None = None,
                 section: str | None = None) -> list[Chunk]:
        vec = self.embedder.get_text_embedding(query)
        conds = []
        if mod_id:
            conds.append(qm.FieldCondition(key="mod_id", match=qm.MatchValue(value=mod_id)))
        if section:
            conds.append(qm.FieldCondition(key="section", match=qm.MatchValue(value=section)))
        flt = qm.Filter(must=conds) if conds else None
        resp = self.client.query_points(
            collection_name=self.collection,
            query=vec,
            limit=top_k,
            query_filter=flt,
            with_payload=True,
        )
        hits = resp.points
        results: list[Chunk] = []
        for h in hits:
            payload = h.payload or {}
            text = payload.pop("text", "")
            md = ChunkMetadata(**{k: payload.get(k) for k in ChunkMetadata.model_fields})
            results.append(Chunk(text=text, metadata=md, score=float(h.score)))
        return results


class HybridRetriever:
    """Vector search + keyword match, merged via RRF (Reciprocal Rank Fusion)."""

    def __init__(self, vector_retriever=None) -> None:
        if vector_retriever:
            self.vector = vector_retriever
        elif settings.use_qdrant:
            self.vector = VectorRetriever()
        else:
            from kb.chroma_retriever import ChromaRetriever
            self.vector = ChromaRetriever()

    def retrieve(self, query: str, top_k: int = 8, mod_id: str | None = None,
                 section: str | None = None) -> list[Chunk]:
        vec_results = self.vector.retrieve(query, top_k=top_k * 2, mod_id=mod_id, section=section)

        # Keyword search: find mods whose descriptions contain query terms
        kw_results = self._keyword_search(query, top_k=top_k, mod_id=mod_id)

        # Merge via RRF
        merged = self._rrf_merge(vec_results, kw_results, k=60, top_k=top_k)
        return merged

    def _keyword_search(self, query: str, top_k: int = 8, mod_id: str | None = None) -> list[Chunk]:
        """Search Qdrant payloads by keyword match on text content."""
        # Extract meaningful keywords (Chinese: split by common delimiters; English: words)
        keywords = re.findall(r'[一-鿿]+|[a-zA-Z]{3,}', query)
        if not keywords:
            return []

        # Build OR filter for each keyword
        kw_conds = []
        for kw in keywords[:5]:  # max 5 keywords
            kw_conds.append(
                qm.FieldCondition(key="text", match=qm.MatchText(text=kw))
            )

        if not kw_conds:
            return []

        # Qdrant requires a text index on the payload field — if not set up, fall back
        # to scanning all points client-side (only for small collections)
        try:
            # Try server-side text match (requires text index on "text" field)
            resp = self.vector.client.query_points(
                collection_name=self.vector.collection,
                query_filter=qm.Filter(should=kw_conds),
                limit=top_k,
                with_payload=True,
            )
            hits = resp.points
        except Exception:
            return []  # text index not set up, skip keyword layer

        results: list[Chunk] = []
        for h in hits:
            payload = h.payload or {}
            text = payload.pop("text", "")
            md = ChunkMetadata(**{k: payload.get(k) for k in ChunkMetadata.model_fields})
            results.append(Chunk(text=text, metadata=md, score=float(h.score or 0.5)))
        return results

    @staticmethod
    def _rrf_merge(vec: list[Chunk], kw: list[Chunk], k: int = 60, top_k: int = 8) -> list[Chunk]:
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
