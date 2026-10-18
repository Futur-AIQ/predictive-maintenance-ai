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

    # Seeded user passwords — override in any public deployment, since the
    # defaults are published in the README
    admin_password: str = "Admin@123"
    engineer_password: str = "Engineer@123"

    # Database
    database_url: str = "sqlite:///./data/pm_system.db"

    # Vector Store
    chroma_persist_dir: str = "./chroma_db"

    # Embeddings — local HuggingFace model, no external server required
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # "sentence-transformers" (torch) or "onnx" (same MiniLM vectors, no torch;
    # ~190 MB less RAM). The index must be built with the same backend it is
    # queried with.
    embedding_backend: str = "sentence-transformers"
    # Where the ONNX model is downloaded; empty = Chroma's default (~/.cache/chroma)
    onnx_model_dir: str = ""

    # Cross-encoder reranking — disable on low-memory hosts (e.g. 512 MB)
    enable_reranker: bool = True

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
        # Browsers send the Origin header without a trailing slash, so
        # "https://app.vercel.app/" would otherwise never match
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
