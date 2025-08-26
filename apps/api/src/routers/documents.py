"""
Роутер для управления документами
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
import logging
import time
import os

from ..schemas.documents import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentStatus,
    DocumentMetadata
)
from ..schemas.common import PaginationParams
from ..services.document_service import DocumentService
from ..middleware.auth import get_current_user
from ..schemas.auth import User
from ..settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Инициализация сервисов
document_service = DocumentService()
settings = get_settings()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Загрузка документа в систему
    
    Поддерживаемые форматы:
    - PDF (векторный и сканированный)
    - DOCX, XLSX
    - HTML, EML
    - Изображения (PNG, JPG, TIFF)
    """
    try:
        start_time = time.time()
        
        logger.info(f"📤 Загрузка документа: {file.filename} от пользователя {current_user.email}")
        
        # Проверяем размер файла
        if file.size and file.size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Файл слишком большой. Максимальный размер: {settings.max_file_size_mb} MB"
            )
        
        # Проверяем MIME тип
        if file.content_type not in settings.supported_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый тип файла: {file.content_type}"
            )
        
        # Загружаем документ
        upload_result = await document_service.upload_document(
            file=file,
            title=title or file.filename,
            description=description,
            tags=tags.split(",") if tags else [],
            user=current_user
        )
        
        upload_time = time.time() - start_time
        
        logger.info(f"✅ Документ загружен за {upload_time:.3f}s: {upload_result.document_id}")
        
        return upload_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка загрузки документа: {str(e)}"
        )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    status: Optional[DocumentStatus] = Query(None),
    mime_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """
    Список документов пользователя
    
    Поддерживает фильтрацию по:
    - Статусу обработки
    - Типу файла
    - Тегам
    - Диапазону дат
    """
    try:
        logger.info(f"📋 Список документов для пользователя {current_user.email}")
        
        # Парсим теги
        tag_list = tags.split(",") if tags else None
        
        # Получаем документы
        documents = await document_service.list_documents(
            user=current_user,
            pagination=pagination,
            status=status,
            mime_type=mime_type,
            tags=tag_list,
            date_from=date_from,
            date_to=date_to
        )
        
        return documents
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка документов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения списка документов: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о документе
    
    Включает:
    - Метаданные
    - Статус обработки
    - Статистику
    - Права доступа
    """
    try:
        logger.info(f"📄 Получение документа {document_id}")
        
        document = await document_service.get_document(
            document_id=document_id,
            user=current_user
        )
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден"
            )
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения документа: {str(e)}"
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Скачивание документа
    
    Проверяет права доступа и возвращает файл
    """
    try:
        logger.info(f"⬇️ Скачивание документа {document_id}")
        
        file_path = await document_service.get_document_file_path(
            document_id=document_id,
            user=current_user
        )
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail="Файл документа не найден"
            )
        
        # Получаем информацию о документе для имени файла
        document_info = await document_service.get_document(
            document_id=document_id,
            user=current_user
        )
        
        filename = document_info.title if document_info.title else f"document_{document_id}"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка скачивания документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка скачивания документа: {str(e)}"
        )

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends()
):
    """
    Получение чанков документа
    
    Возвращает:
    - Текстовые чанки
    - Табличные чанки
    - Координаты и метаданные
    """
    try:
        logger.info(f"📝 Получение чанков документа {document_id}")
        
        chunks = await document_service.get_document_chunks(
            document_id=document_id,
            user=current_user,
            pagination=pagination
        )
        
        return {
            "document_id": document_id,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "pagination": pagination
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения чанков: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения чанков: {str(e)}"
        )

@router.put("/{document_id}/metadata")
async def update_document_metadata(
    document_id: str,
    metadata: DocumentMetadata,
    current_user: User = Depends(get_current_user)
):
    """
    Обновление метаданных документа
    
    Обновляет:
    - Заголовок
    - Описание
    - Теги
    - Кастомные поля
    """
    try:
        logger.info(f"✏️ Обновление метаданных документа {document_id}")
        
        updated_document = await document_service.update_document_metadata(
            document_id=document_id,
            metadata=metadata,
            user=current_user
        )
        
        return updated_document
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления метаданных: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обновления метаданных: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Удаление документа
    
    Удаляет:
    - Файл документа
    - Метаданные
    - Чанки и эмбеддинги
    - Статистику
    """
    try:
        logger.info(f"🗑️ Удаление документа {document_id}")
        
        await document_service.delete_document(
            document_id=document_id,
            user=current_user
        )
        
        return {"message": "Документ успешно удален"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления документа: {str(e)}"
        )

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Переобработка документа
    
    Запускает заново:
    - Парсинг
    - OCR (если необходимо)
    - Извлечение таблиц
    - Чанкование
    - Генерацию эмбеддингов
    """
    try:
        logger.info(f"🔄 Переобработка документа {document_id}")
        
        task_id = await document_service.reprocess_document(
            document_id=document_id,
            user=current_user
        )
        
        return {
            "message": "Документ поставлен в очередь на переобработку",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка переобработки документа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка переобработки документа: {str(e)}"
        )

@router.get("/{document_id}/status")
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получение статуса обработки документа
    
    Возвращает:
    - Текущий этап обработки
    - Прогресс
    - Ошибки (если есть)
    - Время обработки
    """
    try:
        logger.info(f"📊 Статус документа {document_id}")
        
        status = await document_service.get_document_status(
            document_id=document_id,
            user=current_user
        )
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статуса: {str(e)}"
        )

@router.get("/stats/summary")
async def get_documents_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Сводная статистика по документам
    
    Возвращает:
    - Общее количество
    - По типам файлов
    - По статусам
    - По размерам
    """
    try:
        logger.info(f"📈 Сводная статистика документов для пользователя {current_user.email}")
        
        summary = await document_service.get_documents_summary(
            user=current_user
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения сводной статистики: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статистики: {str(e)}"
        )

@router.post("/batch/upload")
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Пакетная загрузка документов
    
    Загружает несколько файлов одновременно
    """
    try:
        logger.info(f"📦 Пакетная загрузка {len(files)} документов")
        
        results = []
        for file in files:
            try:
                result = await document_service.upload_document(
                    file=file,
                    title=file.filename,
                    user=current_user
                )
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "document_id": result.document_id
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "message": "Пакетная загрузка завершена",
            "results": results,
            "total_files": len(files),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"])
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка пакетной загрузки: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка пакетной загрузки: {str(e)}"
        )
