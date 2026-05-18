from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DeepSeek
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    chroma_collection: str = "mcmod_v1"

    sqlite_path: str = "minemate.db"
    chroma_path: str = "chroma"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "auto"  # auto = CUDA if available, else CPU

    # Storage paths
    data_dir: str = "./data"
    hf_home: str = ""       # HuggingFace cache, empty = use default (~/.cache/huggingface)
    hf_endpoint: str = ""   # HuggingFace mirror, empty = use default (hf-mirror.com)

    # Pipeline
    crawl_delay_seconds: float = 1.5
    tutorial_limit_per_mod: int = 30
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval
    top_k: int = 8
    similarity_threshold: float = 0.5

    # Proxy pool (only for pipeline/proxy_crawl.py — bulk crawler).
    # Agent runtime (tools/web_search_mcmod.py) is direct-connection only since Phase 0.
    proxy_api_url: str = ""
    proxy_user: str = ""
    proxy_pass: str = ""

    # App
    log_level: str = "INFO"
    log_dir: str = "data/logs"

    @property
    def resolved_sqlite_path(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.sqlite_path, fallback_subdir="db")

    @property
    def resolved_chroma_path(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.chroma_path, fallback_subdir="chroma")

    @property
    def resolved_conv_dir(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(f"{self.data_dir}/conversations", fallback_subdir="conversations")

    @property
    def resolved_log_dir(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.log_dir, fallback_subdir="logs")


settings = Settings()
