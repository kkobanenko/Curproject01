"""
Схемы для поиска
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SearchRequest(BaseModel):
    """Запрос на поиск"""
    query: str = Field(..., description="Поисковый запрос")
    top_k: int = Field(default=20, ge=1, le=100, description="Количество результатов")
    filters: Optional[Dict[str, Any]] = Field(None, description="Фильтры поиска")
    use_rerank: bool = Field(default=False, description="Использовать переранжирование")
    tenant_id: Optional[str] = Field(None, description="ID тенанта")


class SearchResult(BaseModel):
    """Результат поиска"""
    id: str = Field(..., description="ID чанка")
    doc_id: str = Field(..., description="ID документа")
    kind: str = Field(..., description="Тип чанка (text/table)")
    content: Optional[str] = Field(None, description="Текстовое содержимое")
    table_html: Optional[str] = Field(None, description="HTML таблицы")
    bbox: Optional[Dict[str, Any]] = Field(None, description="Координаты")
    page_no: Optional[int] = Field(None, description="Номер страницы")
    score: float = Field(..., description="Релевантность")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")


class SearchResponse(BaseModel):
    """Ответ на поиск"""
    query: str = Field(..., description="Исходный запрос")
    results: List[SearchResult] = Field(..., description="Результаты поиска")
    total: int = Field(..., description="Общее количество результатов")
    processing_time: float = Field(..., description="Время обработки в секундах")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")


class SearchFilters(BaseModel):
    """Фильтры для поиска"""
    tenant_id: Optional[str] = Field(None, description="ID тенанта")
    doc_type: Optional[str] = Field(None, description="Тип документа")
    date_from: Optional[datetime] = Field(None, description="Дата от")
    date_to: Optional[datetime] = Field(None, description="Дата до")
    tags: Optional[List[str]] = Field(None, description="Теги")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Минимальный скор релевантности")


class SearchType(str, Enum):
    """Тип поиска"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
