import os
from functools import lru_cache

from config.settings import settings

# Set HF cache/env BEFORE importing HF libraries
os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint or "https://hf-mirror.com")
if settings.hf_home:
    os.environ["HF_HOME"] = settings.hf_home

from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # noqa: E402


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
