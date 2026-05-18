from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DeepSeek
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    chroma_collection: str = "mcmod_v1"

    sqlite_path: str = "db/minemate.db"
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

    # Proxy pool — used by pipeline/proxy_crawl.py AND tools/web_search_mcmod.py (Playwright + proxy).
    # Local IPs commonly get banned by mcmod after a crawl session; rotate via proxy.
    proxy_api_url: str = ""
    proxy_user: str = ""
    proxy_pass: str = ""

    # Playwright (Chromium) — used by web_search_mcmod for mcmod yxd_token JS bypass.
    # If set, browser binaries go to this path (avoid C:\Users\...\AppData\Local\ms-playwright).
    playwright_browsers_path: str = ""

    # App
    log_level: str = "INFO"
    log_dir: str = "logs"

    @property
    def resolved_sqlite_path(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.sqlite_path)

    @property
    def resolved_chroma_path(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.chroma_path)

    @property
    def resolved_conv_dir(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(f"{self.data_dir}/conversations")

    @property
    def resolved_log_dir(self) -> Path:
        from config.paths import resolve_data_path
        return resolve_data_path(self.log_dir)


settings = Settings()
