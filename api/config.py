"""Configuration settings for Tensoria API."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Security
    api_key: str = ""  # Required in production! Set via API_KEY env var
    
    # Ollama connection
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120  # seconds
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    
    # Model defaults
    default_model: str = "mistral"
    max_tokens: int = 4096
    default_temperature: float = 0.7
    
    # Supported models (for documentation purposes)
    # These are NOT downloaded automatically
    supported_models: list[str] = [
        "mistral",
        "mistral:7b",
        "mistral:7b-instruct",
        "deepseek-coder",
        "deepseek-coder:6.7b",
        "deepseek-coder:33b",
        "qwen",
        "qwen:7b",
        "qwen:14b",
        "qwen2",
        "qwen2:7b",
        "kimi-k2",  # When available
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
