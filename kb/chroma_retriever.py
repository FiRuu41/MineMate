import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from kb.schemas import Chunk, ChunkMetadata
from llm.embeddings import get_embedder


class ChromaRetriever:
    def __init__(self, embedder=None, collection: str = None):
        self.collection_name = collection or settings.qdrant_collection
        self.embedder = embedder or get_embedder()
        self._client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _get_collection(self):
        return self._client.get_or_create_collection(self.collection_name)

    def retrieve(self, query: str, top_k: int = 8, mod_id: str | None = None,
                 section: str | None = None) -> list[Chunk]:
        vec = self.embedder.get_text_embedding(query)
        where = {}
        if mod_id:
            where["mod_id"] = mod_id
        if section:
            where["section"] = section
        col = self._get_collection()
        results = col.query(
            query_embeddings=[vec],
            n_results=top_k,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                meta = (results["metadatas"][0] or [{}])[i] if results["metadatas"] else {}
                text = (results["documents"][0] or [""])[i] if results["documents"] else ""
                dist = (results["distances"][0] or [0])[i] if results["distances"] else [0]
                md = ChunkMetadata(**{k: meta.get(k) for k in ChunkMetadata.model_fields})
                chunks.append(Chunk(text=text, metadata=md, score=1.0 - float(dist)))
        return chunks
