"""
Роутер для работы с документами
"""
import hashlib
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends, BackgroundTasks
from ..schemas.documents import DocumentInfo, DocumentList, DocumentStatus
from ..services.vectorstore import VectorStoreService

router = APIRouter()

# Зависимости
async def get_vector_store() -> VectorStoreService:
    """Получить сервис векторного хранилища"""
    return VectorStoreService()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None
):
    """Загрузка документа"""
    try:
        # Проверяем тип файла
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/html",
            "text/plain",
            "image/jpeg",
            "image/png"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}"
            )
        
        # Читаем содержимое файла
        content = await file.read()
        
        # Вычисляем SHA256
        sha256 = hashlib.sha256(content).hexdigest()
        
        # Сохраняем файл во временную директорию
        # В продакшене лучше использовать S3 или другое хранилище
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{sha256}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Создаем запись в базе данных
        vector_store = VectorStoreService()
        
        # TODO: Реализовать создание документа в базе
        # Пока возвращаем базовую информацию
        
        return {
            "message": "Document uploaded successfully",
            "file_id": sha256,
            "filename": file.filename,
            "size": len(content),
            "mime_type": file.content_type,
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentList)
async def list_documents(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    tenant_id: Optional[str] = Query(None),
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Получить список документов"""
    try:
        result = await vector_store.list_documents(
            tenant_id=tenant_id,
            page=page,
            size=size
        )
        
        return DocumentList(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document(
    doc_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Получить информацию о документе"""
    try:
        doc_info = await vector_store.get_document_info(doc_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentInfo(**doc_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Получить чанки документа"""
    try:
        chunks = await vector_store.get_document_chunks(doc_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "doc_id": doc_id,
            "chunks": chunks,
            "total": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Удалить документ"""
    try:
        # TODO: Реализовать удаление документа
        # Пока возвращаем заглушку
        
        return {
            "message": "Document deletion not implemented yet",
            "doc_id": doc_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: str):
    """Получить статус обработки документа"""
    try:
        # TODO: Реализовать получение статуса
        # Пока возвращаем заглушку
        
        return DocumentStatus(
            doc_id=doc_id,
            status="completed",
            progress=100.0,
            message="Document processed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
