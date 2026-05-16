import hashlib
import uuid

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config.settings import settings
from kb.schemas import Chunk


class QdrantWriter:
    def __init__(self, collection: str | None = None) -> None:
        self.collection = collection or settings.qdrant_collection
        self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    def recreate(self, dim: int) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )
        logger.info("recreated collection {} dim={}", self.collection, dim)

    def ensure_collection(self, dim: int) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            )

    def delete_collection(self) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)

    def delete_by_mod_id(self, mod_id: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[qm.FieldCondition(key="mod_id", match=qm.MatchValue(value=mod_id))])
            ),
        )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        self.ensure_collection(dim=len(vectors[0]))
        points: list[qm.PointStruct] = []
        for c, v in zip(chunks, vectors, strict=True):
            digest = hashlib.sha1((c.metadata.source_url + c.text).encode("utf-8")).hexdigest()
            pid = str(uuid.UUID(digest[:32]))
            payload = c.metadata.model_dump() | {"text": c.text}
            points.append(qm.PointStruct(id=pid, vector=v, payload=payload))
        self.client.upsert(collection_name=self.collection, points=points)

    def count(self) -> int:
        return self.client.count(collection_name=self.collection, exact=True).count
