from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DeepSeek
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "mcmod"
    mysql_password: str = "mcmod_pwd"
    mysql_db: str = "mcmod_qa"

    # Qdrant
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_collection: str = "mcmod_v1"  # 旧名，等同 chroma_collection（C8 删除）
    chroma_collection: str = "mcmod_v1"

    # Storage mode — default to SQLite + ChromaDB (no Docker needed)
    use_mysql: bool = False        # True = MySQL, False = SQLite
    use_qdrant: bool = False       # True = Qdrant, False = ChromaDB
    sqlite_path: str = "data/minemate.db"
    chroma_path: str = "data/chroma"

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

    # Proxy pool (optional — for mcmod scraping when IP is banned)
    proxy_api_url: str = ""
    proxy_user: str = ""
    proxy_pass: str = ""

    # App
    log_level: str = "INFO"
    log_dir: str = "data/logs"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )

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
