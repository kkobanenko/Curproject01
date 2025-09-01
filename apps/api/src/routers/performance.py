"""
Роутер для мониторинга производительности и оптимизации
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..schemas.auth import User, Permission
from ..schemas.common import PaginatedResponse
from ..middleware.auth import get_current_user, require_permissions
from ..services.performance_monitor import profiler, metrics_collector
from ..services.database_optimizer import db_optimizer, SystemMonitor
from ..services.cache import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["Производительность"])


@router.get("/summary")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """
    Сводка производительности системы
    
    Требуемые разрешения: METRICS_VIEW
    """
    try:
        # Основная сводка
        summary = profiler.get_performance_summary()
        
        # Системные метрики
        system_metrics = SystemMonitor.get_system_metrics()
        
        # Статистика кэша
        cache_stats = await cache_service.get_stats()
        cache_memory = await cache_service.get_memory_usage()
        
        # Статистика БД
        db_stats = await db_optimizer.get_connection_stats()
        
        return {
            "performance": summary,
            "system": system_metrics,
            "cache": {
                "stats": cache_stats,
                "memory": cache_memory
            },
            "database": db_stats,
            "status": "healthy" if summary.get("system_status") == "healthy" else "degraded",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения сводки производительности: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения метрик производительности"
        )


@router.get("/endpoints")
async def get_endpoint_stats(
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("requests", regex="^(requests|response_time|error_rate)$"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """
    Статистика эндпоинтов API
    
    Args:
        limit: Количество эндпоинтов для возврата
        sort_by: Критерий сортировки (requests, response_time, error_rate)
    """
    try:
        endpoint_stats = profiler.get_endpoint_stats(limit * 2)  # Получаем больше для сортировки
        
        # Сортируем по указанному критерию
        if sort_by == "response_time":
            endpoint_stats = sorted(
                endpoint_stats,
                key=lambda x: x["p95_response_time"],
                reverse=True
            )
        elif sort_by == "error_rate":
            endpoint_stats = sorted(
                endpoint_stats,
                key=lambda x: x["error_rate"],
                reverse=True
            )
        else:  # requests
            endpoint_stats = sorted(
                endpoint_stats,
                key=lambda x: x["total_requests"],
                reverse=True
            )
        
        return {
            "endpoints": endpoint_stats[:limit],
            "total_endpoints": len(profiler.endpoint_metrics),
            "sort_by": sort_by,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики эндпоинтов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики эндпоинтов"
        )


@router.get("/slow-endpoints")
async def get_slow_endpoints(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """Самые медленные эндпоинты"""
    try:
        slow_endpoints = profiler.get_slow_endpoints(limit)
        
        return {
            "slow_endpoints": slow_endpoints,
            "threshold_seconds": profiler.slow_request_threshold,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения медленных эндпоинтов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения медленных эндпоинтов"
        )


@router.get("/error-prone-endpoints")
async def get_error_prone_endpoints(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """Эндпоинты с высоким процентом ошибок"""
    try:
        error_endpoints = profiler.get_error_prone_endpoints(limit)
        
        return {
            "error_prone_endpoints": error_endpoints,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения проблемных эндпоинтов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения проблемных эндпоинтов"
        )


@router.get("/metrics/{metric_name}")
async def get_metrics_by_name(
    metric_name: str,
    hours: int = Query(1, ge=1, le=24),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """
    Получение метрик по названию за указанный период
    
    Args:
        metric_name: Название метрики
        hours: Количество часов назад
        limit: Максимальное количество точек данных
    """
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        metrics = profiler.get_metrics_by_name(metric_name, since, limit)
        
        # Преобразуем в формат для графиков
        data_points = [
            {
                "timestamp": m.timestamp.isoformat(),
                "value": m.value,
                "unit": m.unit,
                "tags": m.tags,
                "metadata": m.metadata
            }
            for m in metrics
        ]
        
        # Агрегированная статистика
        values = [m.value for m in metrics]
        aggregated = {}
        if values:
            aggregated = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": sorted(values)[len(values) // 2] if values else 0
            }
        
        return {
            "metric_name": metric_name,
            "period_hours": hours,
            "data_points": data_points,
            "aggregated": aggregated,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения метрик {metric_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения метрик {metric_name}"
        )


@router.get("/database/stats")
async def get_database_stats(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN, Permission.METRICS_VIEW]))
):
    """
    Статистика использования базы данных
    
    Требуемые разрешения: ADMIN или METRICS_VIEW
    """
    try:
        # Статистика использования таблиц
        table_usage = await db_optimizer.analyze_table_usage()
        
        # Статистика использования индексов
        index_usage = await db_optimizer.analyze_index_usage()
        
        # Информация о размерах
        size_info = await db_optimizer.get_database_size_info()
        
        # Статистика подключений
        connection_stats = await db_optimizer.get_connection_stats()
        
        # Статистика запросов от профилировщика
        query_summary = db_optimizer.profiler.get_performance_summary()
        
        return {
            "tables": table_usage,
            "indexes": index_usage,
            "sizes": size_info,
            "connections": connection_stats,
            "queries": query_summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики БД: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики базы данных"
        )


@router.get("/database/slow-queries")
async def get_slow_queries(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Самые медленные запросы к БД
    
    Требуемые разрешения: ADMIN
    """
    try:
        slow_queries = db_optimizer.profiler.get_slow_queries(limit)
        
        return {
            "slow_queries": [
                {
                    "query_hash": q.query_hash,
                    "execution_time": q.execution_time,
                    "rows_returned": q.rows_returned,
                    "query_text": q.query_text,
                    "timestamp": q.timestamp.isoformat(),
                    "user_id": q.user_id,
                    "endpoint": q.endpoint
                }
                for q in slow_queries
            ],
            "threshold_seconds": db_optimizer.profiler.slow_query_threshold,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения медленных запросов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения медленных запросов"
        )


@router.get("/database/recommendations")
async def get_database_recommendations(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Рекомендации по оптимизации БД
    
    Требуемые разрешения: ADMIN
    """
    try:
        # Рекомендации по индексам
        index_recommendations = await db_optimizer.generate_index_recommendations()
        
        # Рекомендации по производительности системы
        system_recommendations = await SystemMonitor.get_performance_recommendations()
        
        return {
            "index_recommendations": [
                {
                    "table_name": rec.table_name,
                    "columns": rec.columns,
                    "index_type": rec.index_type,
                    "reason": rec.reason,
                    "estimated_benefit": rec.estimated_benefit,
                    "priority": rec.priority
                }
                for rec in index_recommendations
            ],
            "system_recommendations": system_recommendations,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения рекомендаций"
        )


@router.post("/database/optimize")
async def optimize_database(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Автоматическая оптимизация БД
    
    Требуемые разрешения: ADMIN
    """
    try:
        result = await db_optimizer.optimize_queries()
        
        return {
            "optimization_result": result,
            "performed_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации БД: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка оптимизации БД: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """Статистика кэша Redis"""
    try:
        # Общая статистика
        stats = await cache_service.get_stats()
        
        # Использование памяти
        memory_usage = await cache_service.get_memory_usage()
        
        return {
            "stats": stats,
            "memory": memory_usage,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики кэша: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики кэша"
        )


@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Паттерн для очистки (например: user:*)"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Очистка кэша
    
    Args:
        pattern: Паттерн ключей для очистки (опционально)
        
    Требуемые разрешения: ADMIN
    """
    try:
        if pattern:
            deleted_count = await cache_service.delete_pattern(pattern)
            message = f"Удалено {deleted_count} ключей по паттерну '{pattern}'"
        else:
            # Очищаем весь кэш (осторожно!)
            deleted_count = await cache_service.delete_pattern("*")
            message = f"Очищен весь кэш. Удалено {deleted_count} ключей"
        
        return {
            "message": message,
            "deleted_keys": deleted_count,
            "pattern": pattern,
            "performed_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки кэша: {str(e)}"
        )


@router.get("/system/metrics")
async def get_system_metrics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """Системные метрики сервера"""
    try:
        metrics = SystemMonitor.get_system_metrics()
        
        return {
            "system_metrics": metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения системных метрик: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения системных метрик"
        )


@router.post("/metrics/collect")
async def trigger_metrics_collection(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Запуск сбора метрик вручную
    
    Требуемые разрешения: ADMIN
    """
    try:
        # Записываем системные метрики
        profiler.record_system_metrics()
        
        # Собираем дополнительные метрики
        cache_stats = await cache_service.get_stats()
        if cache_stats:
            profiler.record_metric("cache_total_keys", cache_stats.get("total_keys", 0), "count")
            profiler.record_metric("cache_hit_rate", cache_stats.get("hit_rate", 0), "percent")
        
        return {
            "message": "Метрики успешно собраны",
            "performed_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка сбора метрик: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сбора метрик: {str(e)}"
        )
