"""
Схемы для ответов RAG системы
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AnswerRequest(BaseModel):
    """Запрос на генерацию ответа"""
    question: str = Field(..., description="Вопрос пользователя")
    top_k: int = Field(default=5, ge=1, le=20, description="Количество источников")
    include_citations: bool = Field(default=True, description="Включить цитаты")
    include_sources: bool = Field(default=True, description="Включить источники")
    max_length: int = Field(default=1000, ge=100, le=5000, description="Максимальная длина ответа")
    creativity: float = Field(default=0.7, ge=0.0, le=1.0, description="Уровень креативности")
    context_window: int = Field(default=4000, ge=1000, le=8000, description="Размер контекстного окна")


class Citation(BaseModel):
    """Цитата из источника"""
    text: str = Field(..., description="Текст цитаты")
    source_id: str = Field(..., description="ID источника")
    source_title: str = Field(..., description="Название источника")
    page: Optional[int] = Field(None, description="Номер страницы")
    score: float = Field(..., description="Релевантность цитаты")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")


class AnswerResponse(BaseModel):
    """Ответ RAG системы"""
    answer: str = Field(..., description="Сгенерированный ответ")
    question: str = Field(..., description="Исходный вопрос")
    citations: List[Citation] = Field(default_factory=list, description="Цитаты из источников")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Источники информации")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в ответе")
    processing_time: float = Field(..., description="Время обработки в секундах")
    tokens_used: int = Field(..., description="Количество использованных токенов")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Информация о модели")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")


class AnswerFeedback(BaseModel):
    """Обратная связь по ответу"""
    answer_id: str = Field(..., description="ID ответа")
    rating: int = Field(..., ge=1, le=5, description="Оценка (1-5)")
    helpful: bool = Field(..., description="Был ли ответ полезен")
    comment: Optional[str] = Field(None, description="Комментарий пользователя")
    user_id: str = Field(..., description="ID пользователя")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")


class AnswerHistory(BaseModel):
    """История ответов"""
    answers: List[AnswerResponse] = Field(..., description="Список ответов")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")


class RAGContext(BaseModel):
    """Контекст для RAG системы"""
    query: str = Field(..., description="Исходный запрос")
    relevant_chunks: List[Dict[str, Any]] = Field(..., description="Релевантные чанки")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные контекста")
    search_time: float = Field(..., description="Время поиска в секундах")
    chunk_count: int = Field(..., description="Количество найденных чанков")
