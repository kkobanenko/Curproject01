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
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")
    
    # Ollama настройки
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_llm_model: str = Field(default="llama3:8b", env="OLLAMA_LLM_MODEL")
    ollama_embed_model: str = Field(default="bge-m3", env="OLLAMA_EMBED_MODEL")
    
    # PostgreSQL настройки
    pg_dsn: str = Field(default="postgresql://postgres:postgres@localhost:5432/rag_app", env="PG_DSN")
    
    # Redis настройки
    redis_url: str = Field(default="redis://localhost:6379/1", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=1, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # JWT настройки
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # ClickHouse настройки
    clickhouse_url: str = Field(default="http://localhost:8123", env="CLICKHOUSE_URL")
    clickhouse_host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=8123, env="CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", env="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="", env="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field(default="rag", env="CLICKHOUSE_DATABASE")
    
    # Email настройки для алертов
    smtp_server: str = Field(default="localhost", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="alerts@rag-system.com", env="SMTP_FROM_EMAIL")
    alert_emails: str = Field(default="admin@rag-system.com", env="ALERT_EMAILS")
    
    # Slack настройки для алертов
    slack_webhook_url: str = Field(default="", env="SLACK_WEBHOOK_URL")
    slack_channel: str = Field(default="#alerts", env="SLACK_CHANNEL")
    
    # Путь к конфигурации
    config_path: str = Field(default="/app/configs/app.toml", env="CONFIG_PATH")
    
    # CORS настройки
    cors_origins: list[str] = Field(default=["*"], env="CORS_ORIGINS")
    allowed_hosts: list[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Файлы настройки
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    supported_mime_types: list[str] = Field(
        default=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                "application/vnd.ms-excel", "text/html", "message/rfc822"],
        env="SUPPORTED_MIME_TYPES"
    )
    
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
