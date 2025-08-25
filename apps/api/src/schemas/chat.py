"""
Схемы для чата
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Сообщение в чате"""
    role: str = Field(..., description="Роль (user/assistant)")
    content: str = Field(..., description="Содержимое сообщения")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")


class ChatRequest(BaseModel):
    """Запрос на генерацию ответа"""
    message: str = Field(..., description="Сообщение пользователя")
    conversation_id: Optional[str] = Field(None, description="ID беседы")
    use_context: bool = Field(default=True, description="Использовать контекст из документов")
    top_k: int = Field(default=5, ge=1, le=20, description="Количество релевантных документов")
    tenant_id: Optional[str] = Field(None, description="ID тенанта")


class Citation(BaseModel):
    """Цитата из документа"""
    doc_id: str = Field(..., description="ID документа")
    chunk_id: str = Field(..., description="ID чанка")
    content: str = Field(..., description="Содержимое цитаты")
    page_no: Optional[int] = Field(None, description="Номер страницы")
    score: float = Field(..., description="Релевантность")
    bbox: Optional[Dict[str, Any]] = Field(None, description="Координаты")


class ChatResponse(BaseModel):
    """Ответ чата"""
    message: str = Field(..., description="Ответ ассистента")
    conversation_id: str = Field(..., description="ID беседы")
    citations: List[Citation] = Field(default_factory=list, description="Цитаты из документов")
    processing_time: float = Field(..., description="Время обработки в секундах")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Временная метка")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")
