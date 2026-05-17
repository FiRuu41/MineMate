import os
from functools import lru_cache

# Default to hf-mirror.com for China-friendly access. Honor user override.
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # noqa: E402

from config.settings import settings  # noqa: E402


def _auto_detect_device() -> str:
    """Auto-detect CUDA GPU, fall back to CPU."""
    if settings.embedding_device != "auto":
        return settings.embedding_device
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    except ImportError:
        device = "cpu"
    return device


@lru_cache(maxsize=1)
def get_embedder() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(
        model_name=settings.embedding_model,
        device=_auto_detect_device(),
        trust_remote_code=True,
    )
