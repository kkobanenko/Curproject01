"""
Схемы для системы webhooks и внешних интеграций
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime
from enum import Enum


class WebhookEventType(str, Enum):
    """Типы событий для webhooks"""
    # Документы
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_SHARED = "document.shared"
    
    # Пользователи
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # RAG операции
    RAG_QUERY_COMPLETED = "rag.query.completed"
    SEARCH_PERFORMED = "search.performed"
    
    # Система
    SYSTEM_ALERT = "system.alert"
    BACKUP_COMPLETED = "backup.completed"
    MAINTENANCE_STARTED = "maintenance.started"
    MAINTENANCE_COMPLETED = "maintenance.completed"
    
    # Безопасность
    SECURITY_VIOLATION = "security.violation"
    LOGIN_FAILED = "login.failed"
    PERMISSION_CHANGED = "permission.changed"
    
    # Кастомные события
    CUSTOM_EVENT = "custom.event"


class WebhookStatus(str, Enum):
    """Статус webhook"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    SUSPENDED = "suspended"


class WebhookDeliveryStatus(str, Enum):
    """Статус доставки webhook"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class WebhookEndpoint(BaseModel):
    """Конфигурация webhook endpoint"""
    id: Optional[int] = None
    name: str = Field(..., description="Название webhook")
    url: HttpUrl = Field(..., description="URL для отправки webhook")
    events: List[WebhookEventType] = Field(..., description="Подписанные события")
    
    # Настройки
    active: bool = Field(default=True, description="Активен ли webhook")
    secret_token: Optional[str] = Field(None, description="Секретный токен для подписи")
    timeout_seconds: int = Field(default=30, description="Таймаут запроса")
    max_retries: int = Field(default=3, description="Максимум повторных попыток")
    retry_delay_seconds: int = Field(default=60, description="Задержка между попытками")
    
    # Фильтры
    tenant_id: Optional[int] = Field(None, description="ID тенанта (None для всех)")
    user_filter: Optional[Dict[str, Any]] = Field(None, description="Фильтр по пользователям")
    content_filter: Optional[Dict[str, Any]] = Field(None, description="Фильтр по содержимому")
    
    # Метаданные
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = Field(None, description="ID создателя")
    last_delivery: Optional[datetime] = Field(None, description="Последняя доставка")
    status: WebhookStatus = Field(default=WebhookStatus.ACTIVE)
    
    @validator('events')
    def validate_events(cls, v):
        if not v:
            raise ValueError("Должно быть указано хотя бы одно событие")
        return v


class WebhookPayload(BaseModel):
    """Полезная нагрузка webhook"""
    event_type: WebhookEventType = Field(..., description="Тип события")
    event_id: str = Field(..., description="Уникальный ID события")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Контекст
    tenant_id: Optional[int] = Field(None, description="ID тенанта")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    
    # Данные события
    data: Dict[str, Any] = Field(..., description="Данные события")
    metadata: Dict[str, Any] = Field(default={}, description="Метаданные события")
    
    # Системная информация
    api_version: str = Field(default="v1", description="Версия API")
    source: str = Field(default="rag-platform", description="Источник события")


class WebhookDelivery(BaseModel):
    """Информация о доставке webhook"""
    id: Optional[int] = None
    webhook_id: int = Field(..., description="ID webhook endpoint")
    event_id: str = Field(..., description="ID события")
    payload: WebhookPayload = Field(..., description="Отправленные данные")
    
    # Доставка
    status: WebhookDeliveryStatus = Field(default=WebhookDeliveryStatus.PENDING)
    attempt_count: int = Field(default=0, description="Количество попыток")
    max_attempts: int = Field(default=3, description="Максимум попыток")
    
    # Результат
    response_status: Optional[int] = Field(None, description="HTTP статус ответа")
    response_body: Optional[str] = Field(None, description="Тело ответа")
    response_headers: Optional[Dict[str, str]] = Field(None, description="Заголовки ответа")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    
    # Времена
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(None, description="Время отправки")
    delivered_at: Optional[datetime] = Field(None, description="Время доставки")
    next_retry_at: Optional[datetime] = Field(None, description="Время следующей попытки")


class WebhookCreate(BaseModel):
    """Схема создания webhook"""
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    events: List[WebhookEventType]
    active: bool = Field(default=True)
    secret_token: Optional[str] = Field(None, min_length=8)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    tenant_id: Optional[int] = None
    user_filter: Optional[Dict[str, Any]] = None
    content_filter: Optional[Dict[str, Any]] = None


class WebhookUpdate(BaseModel):
    """Схема обновления webhook"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[HttpUrl] = None
    events: Optional[List[WebhookEventType]] = None
    active: Optional[bool] = None
    secret_token: Optional[str] = Field(None, min_length=8)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=3600)
    user_filter: Optional[Dict[str, Any]] = None
    content_filter: Optional[Dict[str, Any]] = None


class WebhookStats(BaseModel):
    """Статистика webhook"""
    webhook_id: int
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    average_response_time_ms: float = 0.0
    last_delivery_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    error_rate_percent: float = 0.0


class ExternalAPIConfig(BaseModel):
    """Конфигурация внешнего API"""
    id: Optional[int] = None
    name: str = Field(..., description="Название API")
    base_url: HttpUrl = Field(..., description="Базовый URL API")
    api_type: str = Field(..., description="Тип API (rest, graphql, soap)")
    
    # Аутентификация
    auth_type: str = Field(..., description="Тип аутентификации")
    auth_config: Dict[str, Any] = Field(..., description="Конфигурация аутентификации")
    
    # Настройки
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    rate_limit_requests: int = Field(default=100, description="Запросов в минуту")
    
    # Маппинг данных
    field_mapping: Dict[str, str] = Field(default={}, description="Маппинг полей")
    
    # Метаданные
    tenant_id: int = Field(..., description="ID тенанта")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True)


class DataExportRequest(BaseModel):
    """Запрос на экспорт данных"""
    export_type: str = Field(..., description="Тип экспорта")
    format: str = Field(..., description="Формат (json, csv, xml, excel)")
    
    # Фильтры
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    document_types: Optional[List[str]] = None
    
    # Настройки экспорта
    include_content: bool = Field(default=False, description="Включать содержимое документов")
    include_metadata: bool = Field(default=True, description="Включать метаданные")
    compress: bool = Field(default=False, description="Сжимать результат")
    
    # Ограничения
    max_records: int = Field(default=10000, le=100000)
    chunk_size: int = Field(default=1000, le=5000)


class DataExportJob(BaseModel):
    """Задача экспорта данных"""
    id: str = Field(..., description="ID задачи")
    request: DataExportRequest = Field(..., description="Параметры экспорта")
    status: str = Field(..., description="Статус")
    
    # Прогресс
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    records_processed: int = Field(default=0)
    total_records: Optional[int] = None
    
    # Результат
    download_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    # Метаданные
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: int = Field(..., description="ID пользователя")
    error_message: Optional[str] = None


class DatabaseSync(BaseModel):
    """Конфигурация синхронизации с БД"""
    id: Optional[int] = None
    name: str = Field(..., description="Название синхронизации")
    source_type: str = Field(..., description="Тип источника")
    connection_string: str = Field(..., description="Строка подключения")
    
    # Настройки синхронизации
    sync_direction: str = Field(..., description="Направление (import, export, bidirectional)")
    schedule: str = Field(..., description="Расписание (cron)")
    
    # Маппинг таблиц
    table_mappings: List[Dict[str, Any]] = Field(..., description="Маппинг таблиц")
    
    # Настройки
    batch_size: int = Field(default=1000)
    conflict_resolution: str = Field(default="source_wins")
    
    # Состояние
    tenant_id: int = Field(..., description="ID тенанта")
    active: bool = Field(default=True)
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SyncResult(BaseModel):
    """Результат синхронизации"""
    sync_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = Field(..., description="Статус синхронизации")
    
    # Статистика
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    records_failed: int = 0
    
    # Ошибки
    errors: List[Dict[str, Any]] = Field(default=[])
    warnings: List[str] = Field(default=[])
    
    # Производительность
    duration_seconds: Optional[float] = None
    throughput_records_per_second: Optional[float] = None


class IntegrationEvent(BaseModel):
    """Событие интеграции"""
    id: Optional[int] = None
    event_type: str = Field(..., description="Тип события")
    source: str = Field(..., description="Источник события")
    target: str = Field(..., description="Целевая система")
    
    # Данные
    payload: Dict[str, Any] = Field(..., description="Данные события")
    metadata: Dict[str, Any] = Field(default={})
    
    # Обработка
    status: str = Field(default="pending")
    processed_at: Optional[datetime] = None
    retry_count: int = Field(default=0)
    
    # Контекст
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    correlation_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)