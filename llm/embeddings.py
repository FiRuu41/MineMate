from functools import lru_cache

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from config.settings import settings


@lru_cache(maxsize=1)
def get_embedder() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        trust_remote_code=True,
    )
