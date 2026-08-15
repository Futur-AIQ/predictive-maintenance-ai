from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Predictive Maintenance Intelligence System"
    app_version: str = "1.0.0"
    debug: bool = False

    # Security
    secret_key: str = secrets.token_hex(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite:///./data/pm_system.db"

    # Vector Store
    chroma_persist_dir: str = "./chroma_db"

    # Embeddings — local HuggingFace model, no external server required
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM — OpenRouter (primary)
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LLM — Anthropic (secondary)
    anthropic_api_key: str = ""

    # LLM — OpenAI (fallback)
    openai_api_key: str = ""

    # Data paths
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
