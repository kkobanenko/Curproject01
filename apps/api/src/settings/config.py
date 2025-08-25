"""
Конфигурация приложения
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API настройки
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8080, env="API_PORT")
    
    # Ollama настройки
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_llm_model: str = Field(default="llama3:8b", env="OLLAMA_LLM_MODEL")
    ollama_embed_model: str = Field(default="bge-m3", env="OLLAMA_EMBED_MODEL")
    
    # PostgreSQL настройки
    pg_dsn: str = Field(default="postgresql://postgres:postgres@localhost:5432/rag_app", env="PG_DSN")
    
    # Redis настройки
    redis_url: str = Field(default="redis://localhost:6379/1", env="REDIS_URL")
    
    # ClickHouse настройки
    clickhouse_url: str = Field(default="http://localhost:8123", env="CLICKHOUSE_URL")
    
    # Путь к конфигурации
    config_path: str = Field(default="/app/configs/app.toml", env="CONFIG_PATH")
    
    # RAG настройки
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    top_k: int = Field(default=20, env="TOP_K")
    top_rerank: int = Field(default=3, env="TOP_RERANK")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Получить настройки приложения"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> None:
    """Перезагрузить настройки"""
    global _settings
    _settings = None
