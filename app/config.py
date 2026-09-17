import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Support Ticket AI System"
    app_version: str = "1.0.0"
    debug: bool = True

    data_file_path: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "support_tickets.csv")

    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_timeout: int = 60

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    reference_timestamp: str = os.getenv("REFERENCE_TIMESTAMP", "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()