"""
Роутер для генерации ответов с помощью RAG
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import time

from ..schemas.answers import (
    AnswerRequest,
    AnswerResponse,
    AnswerFeedback,
    Citation,
    RAGContext
)
from ..services.rag_service import RAGService
from ..middleware.auth import get_current_user
from ..schemas.auth import User
from ..settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Инициализация сервисов
rag_service = RAGService()
settings = get_settings()

@router.post("/generate", response_model=AnswerResponse)
async def generate_answer(
    request: AnswerRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Генерация ответа на основе RAG
    
    Процесс:
    1. Поиск релевантных документов
    2. Извлечение контекста
    3. Генерация ответа с помощью LLM
    4. Формирование цитат
    """
    try:
        start_time = time.time()
        
        logger.info(f"🤖 Генерация ответа на вопрос: '{request.question}' от пользователя {current_user.email}")
        
        # Генерируем ответ
        answer = await rag_service.generate_answer(
            question=request.question,
            context=request.context,
            max_length=request.max_length,
            temperature=request.temperature,
            include_citations=request.include_citations,
            user=current_user
        )
        
        generation_time = time.time() - start_time
        
        logger.info(f"✅ Ответ сгенерирован за {generation_time:.3f}s")
        
        return answer
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации ответа: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации ответа: {str(e)}"
        )

@router.post("/chat", response_model=AnswerResponse)
async def chat_conversation(
    request: AnswerRequest,
    conversation_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Чат-режим с поддержкой контекста беседы
    
    Поддерживает:
    - Сохранение истории разговора
    - Контекст предыдущих сообщений
    - Персонализацию ответов
    """
    try:
        start_time = time.time()
        
        logger.info(f"💬 Чат-сообщение: '{request.question}' от пользователя {current_user.email}")
        
        # Генерируем ответ в контексте беседы
        answer = await rag_service.chat_conversation(
            question=request.question,
            conversation_id=conversation_id,
            context=request.context,
            max_length=request.max_length,
            temperature=request.temperature,
            include_citations=request.include_citations,
            user=current_user
        )
        
        chat_time = time.time() - start_time
        
        logger.info(f"✅ Чат-ответ сгенерирован за {chat_time:.3f}s")
        
        return answer
        
    except Exception as e:
        logger.error(f"❌ Ошибка чат-режима: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка чат-режима: {str(e)}"
        )

@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Список бесед пользователя
    
    Возвращает:
    - ID беседы
    - Первый вопрос
    - Количество сообщений
    - Время последней активности
    """
    try:
        logger.info(f"📋 Список бесед для пользователя {current_user.email}")
        
        conversations = await rag_service.list_conversations(
            user=current_user,
            limit=limit,
            offset=offset
        )
        
        return conversations
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка бесед: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения списка бесед: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=List[Dict[str, Any]])
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200)
):
    """
    История конкретной беседы
    
    Возвращает:
    - Вопросы пользователя
    - Ответы системы
    - Временные метки
    - Контекст и цитаты
    """
    try:
        logger.info(f"📜 История беседы {conversation_id}")
        
        history = await rag_service.get_conversation_history(
            conversation_id=conversation_id,
            user=current_user,
            limit=limit
        )
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории беседы: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения истории беседы: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Удаление беседы
    
    Удаляет:
    - Историю сообщений
    - Контекст
    - Метаданные
    """
    try:
        logger.info(f"🗑️ Удаление беседы {conversation_id}")
        
        await rag_service.delete_conversation(
            conversation_id=conversation_id,
            user=current_user
        )
        
        return {"message": "Беседа успешно удалена"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления беседы: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления беседы: {str(e)}"
        )

@router.post("/feedback")
async def submit_answer_feedback(
    feedback: AnswerFeedback,
    current_user: User = Depends(get_current_user)
):
    """
    Отправка обратной связи по ответу
    
    Типы обратной связи:
    - helpful/not_helpful - полезность ответа
    - accurate/inaccurate - точность информации
    - complete/incomplete - полнота ответа
    - relevant/irrelevant - релевантность
    """
    try:
        logger.info(f"💬 Обратная связь по ответу {feedback.answer_id}: {feedback.feedback_type}")
        
        await rag_service.submit_answer_feedback(
            feedback=feedback,
            user=current_user
        )
        
        return {"message": "Обратная связь успешно отправлена"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка отправки обратной связи: {str(e)}"
        )

@router.get("/citations/{citation_id}", response_model=Citation)
async def get_citation_details(
    citation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Детальная информация о цитате
    
    Возвращает:
    - Исходный текст
    - Метаданные документа
    - Координаты (страница, позиция)
    - Контекст
    """
    try:
        logger.info(f"📖 Детали цитаты {citation_id}")
        
        citation = await rag_service.get_citation_details(
            citation_id=citation_id,
            user=current_user
        )
        
        if not citation:
            raise HTTPException(
                status_code=404,
                detail="Цитата не найдена"
            )
        
        return citation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения деталей цитаты: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения деталей цитаты: {str(e)}"
        )

@router.post("/rerank")
async def rerank_context(
    question: str = Query(..., min_length=1),
    context_ids: List[str] = Query(...),
    current_user: User = Depends(get_current_user)
):
    """
    Переранжирование контекста
    
    Использует reranker для улучшения релевантности
    найденных документов к вопросу
    """
    try:
        logger.info(f"🔄 Переранжирование контекста для вопроса: '{question}'")
        
        reranked_context = await rag_service.rerank_context(
            question=question,
            context_ids=context_ids,
            user=current_user
        )
        
        return {
            "question": question,
            "reranked_context": reranked_context,
            "total_contexts": len(reranked_context)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка переранжирования: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка переранжирования: {str(e)}"
        )

@router.get("/context/{context_id}", response_model=RAGContext)
async def get_context_details(
    context_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Детальная информация о контексте
    
    Возвращает:
    - Исходный текст
    - Метаданные
    - Эмбеддинги
    - Статистику использования
    """
    try:
        logger.info(f"📚 Детали контекста {context_id}")
        
        context = await rag_service.get_context_details(
            context_id=context_id,
            user=current_user
        )
        
        if not context:
            raise HTTPException(
                status_code=404,
                detail="Контекст не найден"
            )
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения деталей контекста: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения деталей контекста: {str(e)}"
        )

@router.get("/stats/answers", response_model=Dict[str, Any])
async def get_answers_statistics(
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Статистика по ответам
    
    Возвращает:
    - Количество сгенерированных ответов
    - Среднее время генерации
    - Популярные вопросы
    - Качество ответов (по обратной связи)
    """
    try:
        logger.info(f"📊 Статистика ответов за период {period}")
        
        stats = await rag_service.get_answers_statistics(
            period=period,
            user=current_user
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики ответов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статистики: {str(e)}"
        )

@router.post("/export/conversation")
async def export_conversation(
    conversation_id: str,
    format: str = Query("json", regex="^(json|csv|pdf|txt)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Экспорт беседы
    
    Форматы: JSON, CSV, PDF, TXT
    """
    try:
        logger.info(f"📤 Экспорт беседы {conversation_id} в формате {format}")
        
        # Получаем историю беседы
        history = await rag_service.get_conversation_history(
            conversation_id=conversation_id,
            user=current_user,
            limit=1000  # Большой лимит для экспорта
        )
        
        # Экспортируем
        export_data = await rag_service.export_conversation(
            history=history,
            format=format,
            conversation_id=conversation_id
        )
        
        # Определяем тип контента
        content_type = {
            "json": "application/json",
            "csv": "text/csv",
            "pdf": "application/pdf",
            "txt": "text/plain"
        }[format]
        
        # Определяем имя файла
        filename = f"conversation_{conversation_id}_{int(time.time())}.{format}"
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": content_type
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта беседы: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка экспорта беседы: {str(e)}"
        )
