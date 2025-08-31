"""
API эндпоинты для мониторинга системы
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..middleware.auth import get_current_user
from ..services.metrics_collector import get_metrics_collector
from ..services.quality_monitor import get_quality_monitor
from ..services.resource_monitor import get_resource_monitor
from ..services.alert_system import get_alert_system

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# Pydantic модели для запросов и ответов
class SystemMetricsResponse(BaseModel):
    """Ответ с системными метриками"""
    timestamp: datetime
    service: str
    metrics: Dict[str, Any]


class ResourceUsageResponse(BaseModel):
    """Ответ с метриками использования ресурсов"""
    timestamp: datetime
    service: str
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    process: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class QualityMetricsResponse(BaseModel):
    """Ответ с метриками качества"""
    avg_relevance: float
    avg_precision: float
    avg_recall: float
    avg_f1: float
    avg_response_quality: float
    total_queries: int


class QualityTrendsResponse(BaseModel):
    """Ответ с трендами качества"""
    date: str
    avg_relevance: float
    avg_precision: float
    avg_f1: float
    query_count: int


class AlertResponse(BaseModel):
    """Ответ с алертом"""
    alert_id: str
    alert_type: str
    severity: str
    service: str
    message: str
    timestamp: datetime
    status: str
    metadata: Dict[str, Any]


class AlertAcknowledgeRequest(BaseModel):
    """Запрос на подтверждение алерта"""
    acknowledged_by: str


class AlertResolveRequest(BaseModel):
    """Запрос на разрешение алерта"""
    resolved_by: str


class SearchQualityRequest(BaseModel):
    """Запрос на запись метрик качества поиска"""
    query_id: str
    query_text: str
    results: List[Dict[str, Any]]
    user_feedback: Optional[str] = None


class ResponseQualityRequest(BaseModel):
    """Запрос на запись метрик качества ответа"""
    response_id: str
    response_text: str
    response_time_ms: int
    user_rating: Optional[int] = None


@router.get("/system-metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    service: str = Query("api", description="Название сервиса"),
    current_user: dict = Depends(get_current_user)
):
    """Получение системных метрик"""
    try:
        metrics_collector = get_metrics_collector()
        
        # Сбор текущих метрик
        system_metrics = await metrics_collector.collect_system_metrics(service)
        app_metrics = await metrics_collector.collect_application_metrics(service)
        
        # Объединение метрик
        all_metrics = {}
        for metric in system_metrics + app_metrics:
            all_metrics[metric.name] = {
                'value': metric.value,
                'unit': metric.unit,
                'tags': metric.tags
            }
        
        return SystemMetricsResponse(
            timestamp=datetime.now(timezone.utc),
            service=service,
            metrics=all_metrics
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


@router.get("/resource-usage", response_model=ResourceUsageResponse)
async def get_resource_usage(
    service: str = Query("api", description="Название сервиса"),
    current_user: dict = Depends(get_current_user)
):
    """Получение метрик использования ресурсов"""
    try:
        resource_monitor = get_resource_monitor()
        
        # Сбор метрик ресурсов
        resource_data = await resource_monitor.collect_resource_metrics(service)
        
        if not resource_data:
            raise HTTPException(status_code=500, detail="Failed to collect resource metrics")
        
        return ResourceUsageResponse(
            timestamp=datetime.now(timezone.utc),
            service=service,
            cpu=resource_data.get('cpu', {}),
            memory=resource_data.get('memory', {}),
            disk=resource_data.get('disk', {}),
            network=resource_data.get('network', {}),
            process=resource_data.get('process', {}),
            alerts=resource_data.get('alerts', [])
        )
        
    except Exception as e:
        logger.error(f"Error getting resource usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource usage")


@router.get("/resource-statistics")
async def get_resource_statistics(
    service: str = Query("api", description="Название сервиса"),
    hours: int = Query(24, description="Количество часов для статистики"),
    current_user: dict = Depends(get_current_user)
):
    """Получение статистики использования ресурсов"""
    try:
        resource_monitor = get_resource_monitor()
        
        statistics = await resource_monitor.get_resource_statistics(service, hours)
        
        return {
            "service": service,
            "period_hours": hours,
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error(f"Error getting resource statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource statistics")


@router.get("/quality-metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    tenant_id: str = Query(..., description="ID тенанта"),
    days: int = Query(7, description="Количество дней для статистики"),
    current_user: dict = Depends(get_current_user)
):
    """Получение метрик качества поиска"""
    try:
        quality_monitor = get_quality_monitor()
        
        statistics = await quality_monitor.get_quality_statistics(tenant_id, days)
        
        return QualityMetricsResponse(
            avg_relevance=statistics.get('avg_relevance', 0.0),
            avg_precision=statistics.get('avg_precision', 0.0),
            avg_recall=statistics.get('avg_recall', 0.0),
            avg_f1=statistics.get('avg_f1', 0.0),
            avg_response_quality=statistics.get('avg_response_quality', 0.0),
            total_queries=statistics.get('total_queries', 0)
        )
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get quality metrics")


@router.get("/quality-trends", response_model=List[QualityTrendsResponse])
async def get_quality_trends(
    tenant_id: str = Query(..., description="ID тенанта"),
    days: int = Query(30, description="Количество дней для трендов"),
    current_user: dict = Depends(get_current_user)
):
    """Получение трендов качества поиска"""
    try:
        quality_monitor = get_quality_monitor()
        
        trends = await quality_monitor.get_quality_trends(tenant_id, days)
        
        return [
            QualityTrendsResponse(
                date=trend['date'],
                avg_relevance=trend['avg_relevance'],
                avg_precision=trend['avg_precision'],
                avg_f1=trend['avg_f1'],
                query_count=trend['query_count']
            )
            for trend in trends
        ]
        
    except Exception as e:
        logger.error(f"Error getting quality trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get quality trends")


@router.post("/search-quality")
async def record_search_quality(
    request: SearchQualityRequest,
    tenant_id: str = Query(..., description="ID тенанта"),
    current_user: dict = Depends(get_current_user)
):
    """Запись метрик качества поиска"""
    try:
        quality_monitor = get_quality_monitor()
        
        metrics = await quality_monitor.record_search_quality(
            tenant_id=tenant_id,
            query_id=request.query_id,
            query_text=request.query_text,
            results=request.results,
            user_feedback=request.user_feedback
        )
        
        return {
            "message": "Search quality metrics recorded successfully",
            "metrics": {
                "relevance_score": metrics.relevance_score,
                "precision_score": metrics.precision_score,
                "recall_score": metrics.recall_score,
                "f1_score": metrics.f1_score,
                "response_quality": metrics.response_quality
            }
        }
        
    except Exception as e:
        logger.error(f"Error recording search quality: {e}")
        raise HTTPException(status_code=500, detail="Failed to record search quality")


@router.post("/response-quality")
async def record_response_quality(
    request: ResponseQualityRequest,
    tenant_id: str = Query(..., description="ID тенанта"),
    current_user: dict = Depends(get_current_user)
):
    """Запись метрик качества ответа"""
    try:
        quality_monitor = get_quality_monitor()
        
        metrics = await quality_monitor.record_response_quality(
            tenant_id=tenant_id,
            response_id=request.response_id,
            response_text=request.response_text,
            response_time_ms=request.response_time_ms,
            user_rating=request.user_rating
        )
        
        return {
            "message": "Response quality metrics recorded successfully",
            "metrics": {
                "coherence_score": metrics.coherence_score,
                "relevance_score": metrics.relevance_score,
                "completeness_score": metrics.completeness_score,
                "accuracy_score": metrics.accuracy_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error recording response quality: {e}")
        raise HTTPException(status_code=500, detail="Failed to record response quality")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    service: Optional[str] = Query(None, description="Фильтр по сервису"),
    status: str = Query("active", description="Статус алертов"),
    current_user: dict = Depends(get_current_user)
):
    """Получение алертов"""
    try:
        alert_system = get_alert_system()
        
        if status == "active":
            alerts = await alert_system.get_active_alerts(service)
        else:
            # Здесь можно добавить логику для получения алертов с другим статусом
            alerts = []
        
        return [
            AlertResponse(
                alert_id=alert['alert_id'],
                alert_type=alert['alert_type'],
                severity=alert['severity'],
                service=alert['service'],
                message=alert['message'],
                timestamp=alert['timestamp'],
                status=status,
                metadata=alert.get('metadata', {})
            )
            for alert in alerts
        ]
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: AlertAcknowledgeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Подтверждение алерта"""
    try:
        alert_system = get_alert_system()
        
        success = await alert_system.acknowledge_alert(alert_id, request.acknowledged_by)
        
        if success:
            return {"message": f"Alert {alert_id} acknowledged successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found or already processed")
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: AlertResolveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Разрешение алерта"""
    try:
        alert_system = get_alert_system()
        
        success = await alert_system.resolve_alert(alert_id, request.resolved_by)
        
        if success:
            return {"message": f"Alert {alert_id} resolved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found or already processed")
        
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/health")
async def monitoring_health():
    """Проверка здоровья системы мониторинга"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "components": {}
        }
        
        # Проверка ClickHouse
        try:
            metrics_collector = get_metrics_collector()
            if metrics_collector.clickhouse_client:
                health_status["components"]["clickhouse"] = "healthy"
            else:
                health_status["components"]["clickhouse"] = "unhealthy"
        except Exception:
            health_status["components"]["clickhouse"] = "unhealthy"
        
        # Проверка коллектора метрик
        try:
            metrics_collector = get_metrics_collector()
            health_status["components"]["metrics_collector"] = "healthy"
        except Exception:
            health_status["components"]["metrics_collector"] = "unhealthy"
        
        # Проверка монитора качества
        try:
            quality_monitor = get_quality_monitor()
            health_status["components"]["quality_monitor"] = "healthy"
        except Exception:
            health_status["components"]["quality_monitor"] = "unhealthy"
        
        # Проверка монитора ресурсов
        try:
            resource_monitor = get_resource_monitor()
            health_status["components"]["resource_monitor"] = "healthy"
        except Exception:
            health_status["components"]["resource_monitor"] = "unhealthy"
        
        # Проверка системы алертов
        try:
            alert_system = get_alert_system()
            health_status["components"]["alert_system"] = "healthy"
        except Exception:
            health_status["components"]["alert_system"] = "unhealthy"
        
        # Общий статус
        if any(status == "unhealthy" for status in health_status["components"].values()):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking monitoring health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc),
            "error": str(e)
        }


@router.post("/start-collection")
async def start_metrics_collection(
    service: str = Query("api", description="Название сервиса"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """Запуск сбора метрик"""
    try:
        metrics_collector = get_metrics_collector()
        resource_monitor = get_resource_monitor()
        
        # Запуск сбора метрик в фоне
        background_tasks.add_task(metrics_collector.start_collection, service)
        background_tasks.add_task(resource_monitor.start_monitoring, service)
        
        return {
            "message": f"Metrics collection started for service: {service}",
            "service": service,
            "timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Error starting metrics collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to start metrics collection")


@router.post("/stop-collection")
async def stop_metrics_collection(
    current_user: dict = Depends(get_current_user)
):
    """Остановка сбора метрик"""
    try:
        metrics_collector = get_metrics_collector()
        resource_monitor = get_resource_monitor()
        
        # Остановка сбора метрик
        await metrics_collector.stop_collection()
        await resource_monitor.stop_monitoring()
        
        return {
            "message": "Metrics collection stopped",
            "timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Error stopping metrics collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop metrics collection")
