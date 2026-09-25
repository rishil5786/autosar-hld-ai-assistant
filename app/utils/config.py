"""
AUTOSAR HLD AI - Configuration Module
Centralized configuration using environment variables and .env file.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = os.getenv("APP_NAME", "AUTOSAR HLD AI Assistant")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- LLM ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "mistral")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # Groq (Llama-3)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # HuggingFace
    HF_API_TOKEN: Optional[str] = os.getenv("HF_API_TOKEN")
    HF_MODEL_NAME: str = os.getenv("HF_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.1")

    # --- Embedding ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # --- Vector Store ---
    VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "faiss")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", str(PROJECT_ROOT / "data" / "vector_store"))

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'autosar_hld.db'}")

    # --- Paths ---
    DOCUMENTS_PATH: Path = PROJECT_ROOT / "data" / "documents"
    PROCESSED_PATH: Path = PROJECT_ROOT / "data" / "processed"
    REPORTS_PATH: Path = PROJECT_ROOT / "data" / "reports"
    SAMPLE_HLD_PATH: Path = PROJECT_ROOT / "data" / "sample_hld"

    # Convenient Path Aliases
    UPLOAD_DIR: str = str(PROJECT_ROOT / "data" / "documents")
    DATA_DIR: str = str(PROJECT_ROOT / "data")
    VECTOR_STORE_DIR: str = str(PROJECT_ROOT / "data" / "vector_store")

    # --- OCR ---
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"

    # --- Security ---
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    def __init__(self):
        """Ensure required directories exist."""
        for path in [self.DOCUMENTS_PATH, self.PROCESSED_PATH,
                     self.REPORTS_PATH, self.SAMPLE_HLD_PATH,
                     Path(self.VECTOR_STORE_PATH)]:
            path.mkdir(parents=True, exist_ok=True)

    @property
    def llm_available(self) -> bool:
        """Check if an LLM provider is configured and available."""
        if self.LLM_PROVIDER == "openai" and self.OPENAI_API_KEY:
            return True
        if self.LLM_PROVIDER == "anthropic" and self.ANTHROPIC_API_KEY:
            return True
        if self.LLM_PROVIDER == "groq" and self.GROQ_API_KEY:
            return True
        if self.LLM_PROVIDER == "ollama":
            return True
        if self.LLM_PROVIDER == "huggingface" and self.HF_API_TOKEN:
            return True
        return False


settings = Settings()
