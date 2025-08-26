"""
Роутер для поиска документов
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import time

from ..schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchFilters,
    SearchType
)
from ..schemas.common import PaginationParams
from ..services.search_service import SearchService
from ..middleware.auth import get_current_user
from ..schemas.auth import User
from ..settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Инициализация сервисов
search_service = SearchService()
settings = get_settings()

@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends()
):
    """
    Семантический поиск по документам
    
    Поддерживает:
    - Семантический поиск по эмбеддингам
    - Ключевой поиск по тексту
    - Гибридный поиск (комбинация)
    - Фильтрация по метаданным и ACL
    """
    try:
        start_time = time.time()
        
        logger.info(f"🔍 Поиск: '{request.query}' от пользователя {current_user.email}")
        
        # Выполняем поиск
        results = await search_service.search(
            query=request.query,
            search_type=request.search_type,
            filters=request.filters,
            top_k=request.top_k,
            user=current_user,
            pagination=pagination
        )
        
        # Формируем ответ
        search_time = time.time() - start_time
        
        response = SearchResponse(
            query=request.query,
            search_type=request.search_type,
            results=results,
            total_results=len(results),
            search_time=search_time,
            filters_applied=request.filters,
            pagination=pagination
        )
        
        logger.info(f"✅ Поиск завершен за {search_time:.3f}s, найдено {len(results)} результатов")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка выполнения поиска: {str(e)}"
        )

@router.get("/suggest", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Получение предложений для автодополнения поиска
    
    Возвращает популярные запросы и варианты завершения
    """
    try:
        logger.info(f"💡 Поиск предложений для: '{query}'")
        
        suggestions = await search_service.get_suggestions(
            query=query,
            limit=limit,
            user=current_user
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения предложений: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения предложений: {str(e)}"
        )

@router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_searches(
    limit: int = Query(10, ge=1, le=100),
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Получение популярных поисковых запросов
    
    Периоды: 1d, 7d, 30d, 90d
    """
    try:
        logger.info(f"📊 Популярные запросы за период {period}")
        
        popular_searches = await search_service.get_popular_searches(
            limit=limit,
            period=period,
            user=current_user
        )
        
        return popular_searches
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения популярных запросов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения популярных запросов: {str(e)}"
        )

@router.get("/filters", response_model=Dict[str, Any])
async def get_available_filters(
    current_user: User = Depends(get_current_user)
):
    """
    Получение доступных фильтров для поиска
    
    Возвращает:
    - Доступные типы документов
    - Диапазоны дат
    - Размеры файлов
    - Теги и категории
    """
    try:
        logger.info("🔍 Получение доступных фильтров")
        
        filters = await search_service.get_available_filters(
            user=current_user
        )
        
        return filters
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения фильтров: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения фильтров: {str(e)}"
        )

@router.post("/advanced", response_model=SearchResponse)
async def advanced_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends()
):
    """
    Расширенный поиск с дополнительными параметрами
    
    Поддерживает:
    - Булевы операторы (AND, OR, NOT)
    - Фразовый поиск
    - Поиск по диапазонам
    - Сортировка по релевантности/дате/размеру
    """
    try:
        start_time = time.time()
        
        logger.info(f"🔍 Расширенный поиск: '{request.query}'")
        
        # Выполняем расширенный поиск
        results = await search_service.advanced_search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            user=current_user,
            pagination=pagination
        )
        
        search_time = time.time() - start_time
        
        response = SearchResponse(
            query=request.query,
            search_type=SearchType.ADVANCED,
            results=results,
            total_results=len(results),
            search_time=search_time,
            filters_applied=request.filters,
            pagination=pagination
        )
        
        logger.info(f"✅ Расширенный поиск завершен за {search_time:.3f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка расширенного поиска: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка расширенного поиска: {str(e)}"
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_search_statistics(
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Статистика поиска
    
    Возвращает:
    - Количество поисков
    - Среднее время ответа
    - Популярные запросы
    - Успешность поиска
    """
    try:
        logger.info(f"📊 Статистика поиска за период {period}")
        
        stats = await search_service.get_search_statistics(
            period=period,
            user=current_user
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статистики: {str(e)}"
        )

@router.post("/feedback")
async def submit_search_feedback(
    search_id: str,
    query: str,
    feedback_type: str = Query(..., regex="^(relevant|irrelevant|useful|not_useful)$"),
    rating: Optional[int] = Query(None, ge=1, le=5),
    comment: Optional[str] = Query(None, max_length=500),
    current_user: User = Depends(get_current_user)
):
    """
    Отправка обратной связи по результатам поиска
    
    Типы обратной связи:
    - relevant/irrelevant - релевантность результатов
    - useful/not_useful - полезность результатов
    """
    try:
        logger.info(f"💬 Обратная связь по поиску {search_id}: {feedback_type}")
        
        await search_service.submit_search_feedback(
            search_id=search_id,
            query=query,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            user=current_user
        )
        
        return {"message": "Обратная связь успешно отправлена"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки обратной связи: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка отправки обратной связи: {str(e)}"
        )

@router.get("/export")
async def export_search_results(
    query: str = Query(..., min_length=1),
    format: str = Query("json", regex="^(json|csv|pdf)$"),
    search_type: SearchType = SearchType.SEMANTIC,
    top_k: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """
    Экспорт результатов поиска
    
    Форматы: JSON, CSV, PDF
    """
    try:
        logger.info(f"📤 Экспорт результатов поиска '{query}' в формате {format}")
        
        # Выполняем поиск
        results = await search_service.search(
            query=query,
            search_type=search_type,
            top_k=top_k,
            user=current_user
        )
        
        # Экспортируем результаты
        export_data = await search_service.export_results(
            results=results,
            format=format,
            query=query
        )
        
        # Определяем тип контента
        content_type = {
            "json": "application/json",
            "csv": "text/csv",
            "pdf": "application/pdf"
        }[format]
        
        # Определяем имя файла
        filename = f"search_results_{query[:50]}_{int(time.time())}.{format}"
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": content_type
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка экспорта результатов: {str(e)}"
        )
