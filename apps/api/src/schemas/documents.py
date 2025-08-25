"""
Схемы для документов
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentUpload(BaseModel):
    """Загрузка документа"""
    title: Optional[str] = Field(None, description="Название документа")
    tenant_id: Optional[str] = Field(None, description="ID тенанта")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")


class DocumentInfo(BaseModel):
    """Информация о документе"""
    id: str = Field(..., description="ID документа")
    title: Optional[str] = Field(None, description="Название")
    source_path: Optional[str] = Field(None, description="Путь к исходному файлу")
    mime_type: Optional[str] = Field(None, description="MIME-тип")
    sha256: str = Field(..., description="SHA256 хеш")
    size_bytes: Optional[int] = Field(None, description="Размер в байтах")
    tenant_id: str = Field(..., description="ID тенанта")
    created_at: datetime = Field(..., description="Дата создания")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")
    chunk_count: int = Field(default=0, description="Количество чанков")


class DocumentList(BaseModel):
    """Список документов"""
    documents: List[DocumentInfo] = Field(..., description="Документы")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")


class DocumentStatus(BaseModel):
    """Статус обработки документа"""
    doc_id: str = Field(..., description="ID документа")
    status: str = Field(..., description="Статус (processing/completed/failed)")
    progress: float = Field(..., description="Прогресс (0-100)")
    message: Optional[str] = Field(None, description="Сообщение о статусе")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")
