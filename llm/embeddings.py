import os
from functools import lru_cache

# Default to hf-mirror.com for China-friendly access. Honor user override.
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # noqa: E402

from config.settings import settings  # noqa: E402


@lru_cache(maxsize=1)
def get_embedder() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        trust_remote_code=True,
    )
