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


class DocumentUploadResponse(BaseModel):
    """Ответ на загрузку документа"""
    doc_id: str = Field(..., description="ID загруженного документа")
    title: str = Field(..., description="Название документа")
    status: str = Field(..., description="Статус загрузки")
    message: str = Field(..., description="Сообщение о результате")
    created_at: datetime = Field(..., description="Время загрузки")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Метаданные")


class DocumentUpdate(BaseModel):
    """Обновление документа"""
    title: Optional[str] = Field(None, description="Новое название")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Новые метаданные")
    tags: Optional[List[str]] = Field(None, description="Теги")


class DocumentDelete(BaseModel):
    """Удаление документа"""
    doc_id: str = Field(..., description="ID документа для удаления")
    force: bool = Field(default=False, description="Принудительное удаление")


class DocumentListResponse(BaseModel):
    """Ответ со списком документов"""
    documents: List[DocumentInfo] = Field(..., description="Список документов")
    total: int = Field(..., description="Общее количество документов")
    page: int = Field(..., description="Текущая страница")
    size: int = Field(..., description="Размер страницы")
    has_next: bool = Field(..., description="Есть ли следующая страница")
    has_prev: bool = Field(..., description="Есть ли предыдущая страница")


class DocumentMetadata(BaseModel):
    """Метаданные документа"""
    title: Optional[str] = Field(None, description="Название документа")
    author: Optional[str] = Field(None, description="Автор")
    description: Optional[str] = Field(None, description="Описание")
    tags: List[str] = Field(default_factory=list, description="Теги")
    category: Optional[str] = Field(None, description="Категория")
    language: Optional[str] = Field(default="ru", description="Язык")
    created_date: Optional[datetime] = Field(None, description="Дата создания документа")
    modified_date: Optional[datetime] = Field(None, description="Дата изменения документа")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Пользовательские поля")
