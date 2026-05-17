from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DeepSeek
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # MySQL
    mysql_host: str
    mysql_port: int = 3306
    mysql_user: str
    mysql_password: str
    mysql_db: str

    # Qdrant
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_collection: str = "mcmod_v1"

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

    # App
    log_level: str = "INFO"
    log_dir: str = "data/logs"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )


settings = Settings()
