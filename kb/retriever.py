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

    def retrieve(self, query: str, top_k: int = 8, mod_id: str | None = None, section: str | None = None) -> list[Chunk]:
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
