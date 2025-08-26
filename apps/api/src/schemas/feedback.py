"""
Схемы для системы обратной связи
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FeedbackType(str, Enum):
    """Типы обратной связи"""
    GENERAL = "general"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    QUESTION = "question"
    COMPLAINT = "complaint"
    PRAISE = "praise"


class FeedbackCategory(str, Enum):
    """Категории обратной связи"""
    UI_UX = "ui_ux"
    FUNCTIONALITY = "functionality"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    INTEGRATION = "integration"
    OTHER = "other"


class FeedbackRequest(BaseModel):
    """Запрос на создание обратной связи"""
    type: str = Field(..., description="Тип обратной связи")
    content: str = Field(..., description="Содержание обратной связи")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Оценка (1-5)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")


class FeedbackResponse(BaseModel):
    """Ответ на обратную связь"""
    id: str = Field(..., description="ID обратной связи")
    type: str = Field(..., description="Тип обратной связи")
    content: str = Field(..., description="Содержание")
    rating: Optional[int] = Field(None, description="Оценка")
    status: str = Field(..., description="Статус обработки")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")


class FeedbackList(BaseModel):
    """Список обратной связи"""
    feedbacks: List[FeedbackResponse] = Field(..., description="Список обратной связи")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")


class FeedbackStats(BaseModel):
    """Статистика обратной связи"""
    total_feedbacks: int = Field(..., description="Общее количество")
    average_rating: float = Field(..., description="Средняя оценка")
    rating_distribution: Dict[int, int] = Field(..., description="Распределение оценок")
    type_distribution: Dict[str, int] = Field(..., description="Распределение по типам")
    recent_feedbacks: int = Field(..., description="Количество за последние 7 дней")


class FeedbackSubmission(BaseModel):
    """Отправка обратной связи"""
    feedback_type: str = Field(..., description="Тип обратной связи")
    content: str = Field(..., description="Содержание")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Оценка")
    user_id: str = Field(..., description="ID пользователя")
    session_id: Optional[str] = Field(None, description="ID сессии")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")


class FeedbackAnalytics(BaseModel):
    """Аналитика обратной связи"""
    period_start: datetime = Field(..., description="Начало периода")
    period_end: datetime = Field(..., description="Конец периода")
    total_submissions: int = Field(..., description="Общее количество отправок")
    average_rating: float = Field(..., description="Средняя оценка")
    rating_trend: List[Dict[str, Any]] = Field(..., description="Тренд оценок по времени")
    category_distribution: Dict[str, int] = Field(..., description="Распределение по категориям")
    sentiment_analysis: Dict[str, float] = Field(..., description="Анализ настроений")
    top_issues: List[Dict[str, Any]] = Field(..., description="Топ проблем")
