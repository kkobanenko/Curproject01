"""
Схемы для webhook системы
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WebhookEventType(str, Enum):
    """Типы webhook событий"""
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_FAILED = "document_failed"
    SEARCH_PERFORMED = "search_performed"
    ANSWER_GENERATED = "answer_generated"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    USER_LOGGED_IN = "user_logged_in"
    SYSTEM_ALERT = "system_alert"


class WebhookPayload(BaseModel):
    """Полезная нагрузка webhook"""
    event_type: WebhookEventType = Field(..., description="Тип события")
    event_id: str = Field(..., description="Уникальный ID события")
    timestamp: datetime = Field(..., description="Временная метка события")
    data: Dict[str, Any] = Field(..., description="Данные события")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")


class WebhookRequest(BaseModel):
    """Запрос на создание webhook"""
    url: str = Field(..., description="URL для отправки webhook")
    events: List[WebhookEventType] = Field(..., description="Типы событий для отслеживания")
    secret: Optional[str] = Field(None, description="Секретный ключ для подписи")
    description: Optional[str] = Field(None, description="Описание webhook")
    active: bool = Field(default=True, description="Активен ли webhook")


class WebhookResponse(BaseModel):
    """Ответ webhook системы"""
    id: str = Field(..., description="ID webhook")
    url: str = Field(..., description="URL для отправки")
    events: List[WebhookEventType] = Field(..., description="Типы событий")
    status: str = Field(..., description="Статус webhook")
    last_delivery: Optional[datetime] = Field(None, description="Последняя доставка")
    delivery_count: int = Field(..., description="Количество доставок")
    error_count: int = Field(..., description="Количество ошибок")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")


class WebhookDelivery(BaseModel):
    """Доставка webhook"""
    id: str = Field(..., description="ID доставки")
    webhook_id: str = Field(..., description="ID webhook")
    event_id: str = Field(..., description="ID события")
    status: str = Field(..., description="Статус доставки")
    response_code: Optional[int] = Field(None, description="HTTP код ответа")
    response_body: Optional[str] = Field(None, description="Тело ответа")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    delivery_time: datetime = Field(..., description="Время доставки")
    retry_count: int = Field(..., description="Количество попыток")


class WebhookEvent(BaseModel):
    """Событие webhook"""
    id: str = Field(..., description="ID события")
    event_type: WebhookEventType = Field(..., description="Тип события")
    source: str = Field(..., description="Источник события")
    data: Dict[str, Any] = Field(..., description="Данные события")
    timestamp: datetime = Field(..., description="Временная метка")
    processed: bool = Field(default=False, description="Обработано ли событие")
    webhook_ids: List[str] = Field(default_factory=list, description="ID webhook для отправки")
