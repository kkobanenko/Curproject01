"""
Роутер для сбора обратной связи
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging
import time

from ..schemas.feedback import (
    FeedbackSubmission,
    FeedbackResponse,
    FeedbackType,
    FeedbackCategory,
    FeedbackAnalytics
)
from ..services.feedback_service import FeedbackService
from ..middleware.auth import get_current_user
from ..schemas.auth import User
from ..settings import get_settings
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Инициализация сервисов
feedback_service = FeedbackService()
settings = get_settings()

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackSubmission,
    current_user: User = Depends(get_current_user)
):
    """
    Отправка обратной связи
    
    Поддерживает:
    - Оценку ответов
    - Оценку поиска
    - Общие комментарии
    - Технические проблемы
    """
    try:
        start_time = time.time()
        
        logger.info(f"💬 Обратная связь от пользователя {current_user.email}: {feedback.feedback_type}")
        
        # Сохраняем обратную связь
        result = await feedback_service.submit_feedback(
            feedback=feedback,
            user=current_user
        )
        
        submission_time = time.time() - start_time
        
        logger.info(f"✅ Обратная связь сохранена за {submission_time:.3f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка отправки обратной связи: {str(e)}"
        )

@router.get("/types", response_model=List[Dict[str, Any]])
async def get_feedback_types():
    """
    Получение доступных типов обратной связи
    
    Возвращает:
    - Типы обратной связи
    - Категории
    - Описания
    """
    try:
        logger.info("📋 Получение типов обратной связи")
        
        types = await feedback_service.get_feedback_types()
        
        return types
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения типов обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения типов обратной связи: {str(e)}"
        )

@router.get("/user", response_model=List[FeedbackResponse])
async def get_user_feedback(
    current_user: User = Depends(get_current_user),
    feedback_type: Optional[FeedbackType] = Query(None),
    category: Optional[FeedbackCategory] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Получение обратной связи пользователя
    
    Возвращает:
    - История обратной связи
    - Фильтрация по типу и категории
    - Пагинация
    """
    try:
        logger.info(f"📋 Обратная связь пользователя {current_user.email}")
        
        feedback_list = await feedback_service.get_user_feedback(
            user=current_user,
            feedback_type=feedback_type,
            category=category,
            limit=limit,
            offset=offset
        )
        
        return feedback_list
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения обратной связи пользователя: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения обратной связи: {str(e)}"
        )

@router.get("/analytics", response_model=FeedbackAnalytics)
async def get_feedback_analytics(
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    feedback_type: Optional[FeedbackType] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Аналитика обратной связи
    
    Возвращает:
    - Статистику по типам
    - Тренды
    - Распределение оценок
    - Популярные темы
    """
    try:
        logger.info(f"📊 Аналитика обратной связи за период {period}")
        
        analytics = await feedback_service.get_feedback_analytics(
            period=period,
            feedback_type=feedback_type,
            user=current_user
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения аналитики: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения аналитики: {str(e)}"
        )

@router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_feedback_topics(
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Популярные темы обратной связи
    
    Возвращает:
    - Часто упоминаемые темы
    - Количество упоминаний
    - Тренды
    """
    try:
        logger.info(f"🔥 Популярные темы обратной связи за период {period}")
        
        topics = await feedback_service.get_popular_feedback_topics(
            period=period,
            limit=limit,
            user=current_user
        )
        
        return topics
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения популярных тем: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения популярных тем: {str(e)}"
        )

@router.put("/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    feedback: FeedbackSubmission,
    current_user: User = Depends(get_current_user)
):
    """
    Обновление обратной связи
    
    Позволяет пользователю изменить:
    - Оценку
    - Комментарий
    - Категорию
    """
    try:
        logger.info(f"✏️ Обновление обратной связи {feedback_id}")
        
        updated_feedback = await feedback_service.update_feedback(
            feedback_id=feedback_id,
            feedback=feedback,
            user=current_user
        )
        
        return updated_feedback
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обновления обратной связи: {str(e)}"
        )

@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Удаление обратной связи
    
    Пользователь может удалить свою обратную связь
    """
    try:
        logger.info(f"🗑️ Удаление обратной связи {feedback_id}")
        
        await feedback_service.delete_feedback(
            feedback_id=feedback_id,
            user=current_user
        )
        
        return {"message": "Обратная связь успешно удалена"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления обратной связи: {str(e)}"
        )

@router.post("/bulk")
async def submit_bulk_feedback(
    feedback_list: List[FeedbackSubmission],
    current_user: User = Depends(get_current_user)
):
    """
    Пакетная отправка обратной связи
    
    Позволяет отправить несколько отзывов одновременно
    """
    try:
        logger.info(f"📦 Пакетная обратная связь: {len(feedback_list)} отзывов от пользователя {current_user.email}")
        
        results = []
        for feedback in feedback_list:
            try:
                result = await feedback_service.submit_feedback(
                    feedback=feedback,
                    user=current_user
                )
                results.append({
                    "status": "success",
                    "feedback_id": result.feedback_id
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "message": "Пакетная обратная связь обработана",
            "results": results,
            "total": len(feedback_list),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"])
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка пакетной обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка пакетной обратной связи: {str(e)}"
        )

@router.get("/export")
async def export_feedback(
    format: str = Query("json", regex="^(json|csv|pdf)$"),
    period: str = Query("30d", regex="^(1d|7d|30d|90d)$"),
    feedback_type: Optional[FeedbackType] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Экспорт обратной связи
    
    Форматы: JSON, CSV, PDF
    """
    try:
        logger.info(f"📤 Экспорт обратной связи в формате {format} за период {period}")
        
        # Получаем обратную связь
        feedback_data = await feedback_service.get_user_feedback(
            user=current_user,
            feedback_type=feedback_type,
            limit=10000,  # Большой лимит для экспорта
            offset=0
        )
        
        # Экспортируем
        export_data = await feedback_service.export_feedback(
            feedback_data=feedback_data,
            format=format,
            period=period
        )
        
        # Определяем тип контента
        content_type = {
            "json": "application/json",
            "csv": "text/csv",
            "pdf": "application/pdf"
        }[format]
        
        # Определяем имя файла
        filename = f"feedback_export_{period}_{int(time.time())}.{format}"
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": content_type
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка экспорта: {str(e)}"
        )

@router.get("/stats/summary")
async def get_feedback_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Сводная статистика по обратной связи
    
    Возвращает:
    - Общее количество отзывов
    - Распределение по типам
    - Средние оценки
    - Тренды
    """
    try:
        logger.info(f"📊 Сводная статистика обратной связи для пользователя {current_user.email}")
        
        summary = await feedback_service.get_feedback_summary(
            user=current_user
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения сводной статистики: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статистики: {str(e)}"
        )
