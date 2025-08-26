"""
Общие схемы для API
"""
from typing import Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class HealthResponse(BaseModel):
    """Ответ на проверку здоровья сервиса"""
    status: str = Field(..., description="Статус сервиса")
    message: str = Field(..., description="Сообщение")
    version: str = Field(..., description="Версия API")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали проверки")


class ErrorResponse(BaseModel):
    """Схема ошибки"""
    error: str = Field(..., description="Тип ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[str] = Field(None, description="Детали ошибки")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    page: int = Field(default=1, ge=1, description="Номер страницы")
    size: int = Field(default=20, ge=1, le=100, description="Размер страницы")


class PaginatedResponse(BaseModel, Generic[T]):
    """Ответ с пагинацией"""
    items: list[T] = Field(..., description="Элементы")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")
