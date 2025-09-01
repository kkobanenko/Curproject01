"""
Система мониторинга производительности и профилирования
"""
import time
import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from functools import wraps
import psutil
import threading
from collections import deque, defaultdict

from ..settings import get_settings
from .cache import cache_service, CacheKeyBuilder

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PerformanceMetric:
    """Метрика производительности"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointMetrics:
    """Метрики эндпоинта"""
    endpoint: str
    method: str
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    status_codes: Dict[int, int] = field(default_factory=dict)
    error_count: int = 0
    total_requests: int = 0
    last_request: Optional[datetime] = None
    
    def add_request(self, response_time: float, status_code: int):
        """Добавление запроса в метрики"""
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        self.total_requests += 1
        self.last_request = datetime.utcnow()
        
        if status_code >= 400:
            self.error_count += 1
    
    @property
    def avg_response_time(self) -> float:
        """Среднее время ответа"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def p95_response_time(self) -> float:
        """95-й процентиль времени ответа"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]
    
    @property
    def error_rate(self) -> float:
        """Процент ошибок"""
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100
    
    @property
    def requests_per_minute(self) -> float:
        """Запросов в минуту"""
        if not self.last_request:
            return 0.0
        
        # Считаем запросы за последнюю минуту
        minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_requests = sum(1 for _ in range(min(len(self.response_times), 60)))
        return recent_requests


class PerformanceProfiler:
    """Профилировщик производительности"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self.system_metrics_history: deque = deque(maxlen=1440)  # 24 часа с интервалом 1 минута
        self.max_metrics = 100000
        self.slow_request_threshold = 2.0  # секунды
        
        # Настройки алертов
        self.alert_thresholds = {
            "response_time_p95": 5.0,  # секунды
            "error_rate": 5.0,         # процент
            "memory_usage": 85.0,      # процент
            "cpu_usage": 80.0,         # процент
            "disk_usage": 90.0         # процент
        }
        
        # Счетчики для алертов
        self.alert_counters = defaultdict(int)
        self.last_alerts = {}
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Запись метрики производительности"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
        
        # Ограничиваем количество метрик
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
        
        # Проверяем пороги для алертов
        self._check_alert_thresholds(name, value)
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_id: Optional[int] = None,
        request_size: int = 0,
        response_size: int = 0
    ):
        """Запись метрики HTTP запроса"""
        endpoint_key = f"{method} {endpoint}"
        
        if endpoint_key not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint_key] = EndpointMetrics(
                endpoint=endpoint,
                method=method
            )
        
        self.endpoint_metrics[endpoint_key].add_request(response_time, status_code)
        
        # Записываем общие метрики
        self.record_metric("http_request_duration", response_time, "seconds", {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        })
        
        if request_size > 0:
            self.record_metric("http_request_size", request_size, "bytes", {
                "endpoint": endpoint,
                "method": method
            })
        
        if response_size > 0:
            self.record_metric("http_response_size", response_size, "bytes", {
                "endpoint": endpoint,
                "method": method
            })
        
        # Логируем медленные запросы
        if response_time > self.slow_request_threshold:
            logger.warning(
                f"Slow request: {method} {endpoint} took {response_time:.3f}s "
                f"(status: {status_code}, user: {user_id})"
            )
    
    def record_database_query(
        self,
        query_hash: str,
        execution_time: float,
        rows_affected: int = 0,
        query_type: str = "unknown"
    ):
        """Запись метрики запроса к БД"""
        self.record_metric("database_query_duration", execution_time, "seconds", {
            "query_hash": query_hash,
            "query_type": query_type
        }, {
            "rows_affected": rows_affected
        })
    
    def record_cache_operation(
        self,
        operation: str,
        hit: bool,
        duration: float = 0.0,
        key_pattern: str = ""
    ):
        """Запись метрики операции кэша"""
        self.record_metric("cache_operation_duration", duration, "seconds", {
            "operation": operation,
            "hit": str(hit),
            "key_pattern": key_pattern
        })
        
        # Отдельная метрика для hit rate
        self.record_metric("cache_hit", 1.0 if hit else 0.0, "boolean", {
            "operation": operation,
            "key_pattern": key_pattern
        })
    
    def record_system_metrics(self):
        """Запись системных метрик"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record_metric("system_cpu_usage", cpu_percent, "percent")
            
            # Память
            memory = psutil.virtual_memory()
            self.record_metric("system_memory_usage", memory.percent, "percent")
            self.record_metric("system_memory_available", memory.available, "bytes")
            
            # Диск
            disk = psutil.disk_usage('/')
            self.record_metric("system_disk_usage", disk.percent, "percent")
            self.record_metric("system_disk_free", disk.free, "bytes")
            
            # Процессы
            try:
                process = psutil.Process()
                self.record_metric("process_memory_rss", process.memory_info().rss, "bytes")
                self.record_metric("process_cpu_percent", process.cpu_percent(), "percent")
                self.record_metric("process_num_threads", process.num_threads(), "count")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Сохраняем для истории
            system_snapshot = {
                "timestamp": datetime.utcnow(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            }
            self.system_metrics_history.append(system_snapshot)
            
        except Exception as e:
            logger.error(f"Ошибка записи системных метрик: {e}")
    
    def _check_alert_thresholds(self, metric_name: str, value: float):
        """Проверка порогов для алертов"""
        threshold_key = None
        
        # Маппинг метрик на пороги
        if metric_name == "http_request_duration":
            threshold_key = "response_time_p95"
        elif metric_name == "system_memory_usage":
            threshold_key = "memory_usage"
        elif metric_name == "system_cpu_usage":
            threshold_key = "cpu_usage"
        elif metric_name == "system_disk_usage":
            threshold_key = "disk_usage"
        
        if threshold_key and threshold_key in self.alert_thresholds:
            threshold = self.alert_thresholds[threshold_key]
            
            if value > threshold:
                self.alert_counters[threshold_key] += 1
                
                # Ограничиваем частоту алертов
                last_alert = self.last_alerts.get(threshold_key, datetime.min)
                if datetime.utcnow() - last_alert > timedelta(minutes=5):
                    logger.warning(
                        f"Performance alert: {metric_name} = {value} exceeds threshold {threshold}"
                    )
                    self.last_alerts[threshold_key] = datetime.utcnow()
    
    def get_endpoint_stats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Статистика эндпоинтов"""
        stats = []
        
        for endpoint_key, metrics in self.endpoint_metrics.items():
            stats.append({
                "endpoint": metrics.endpoint,
                "method": metrics.method,
                "total_requests": metrics.total_requests,
                "avg_response_time": round(metrics.avg_response_time, 3),
                "p95_response_time": round(metrics.p95_response_time, 3),
                "error_rate": round(metrics.error_rate, 2),
                "requests_per_minute": round(metrics.requests_per_minute, 2),
                "status_codes": dict(metrics.status_codes),
                "last_request": metrics.last_request.isoformat() if metrics.last_request else None
            })
        
        # Сортируем по количеству запросов
        return sorted(stats, key=lambda x: x["total_requests"], reverse=True)[:limit]
    
    def get_slow_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Самые медленные эндпоинты"""
        endpoint_stats = self.get_endpoint_stats()
        return sorted(
            endpoint_stats,
            key=lambda x: x["p95_response_time"],
            reverse=True
        )[:limit]
    
    def get_error_prone_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Эндпоинты с высоким процентом ошибок"""
        endpoint_stats = self.get_endpoint_stats()
        return sorted(
            [s for s in endpoint_stats if s["error_rate"] > 0],
            key=lambda x: x["error_rate"],
            reverse=True
        )[:limit]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Сводка производительности"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        # Метрики за последний час
        recent_metrics = [m for m in self.metrics if m.timestamp > last_hour]
        
        # Группируем по названиям
        metric_groups = defaultdict(list)
        for metric in recent_metrics:
            metric_groups[metric.name].append(metric.value)
        
        summary = {
            "total_requests": sum(em.total_requests for em in self.endpoint_metrics.values()),
            "avg_response_time": 0.0,
            "error_rate": 0.0,
            "cache_hit_rate": 0.0,
            "system_status": "healthy",
            "alerts_active": len([k for k, v in self.alert_counters.items() if v > 0]),
            "metrics_collected": len(recent_metrics),
            "analyzed_at": now.isoformat()
        }
        
        # Средние значения метрик
        if "http_request_duration" in metric_groups:
            summary["avg_response_time"] = round(
                sum(metric_groups["http_request_duration"]) / len(metric_groups["http_request_duration"]), 3
            )
        
        # Cache hit rate
        if "cache_hit" in metric_groups:
            cache_hits = metric_groups["cache_hit"]
            summary["cache_hit_rate"] = round(
                (sum(cache_hits) / len(cache_hits)) * 100, 2
            ) if cache_hits else 0.0
        
        # Общий error rate
        total_requests = sum(em.total_requests for em in self.endpoint_metrics.values())
        total_errors = sum(em.error_count for em in self.endpoint_metrics.values())
        summary["error_rate"] = round(
            (total_errors / total_requests) * 100, 2
        ) if total_requests > 0 else 0.0
        
        # Статус системы
        if any(self.alert_counters.values()):
            summary["system_status"] = "degraded"
        if summary["error_rate"] > 10 or summary["avg_response_time"] > 5:
            summary["system_status"] = "critical"
        
        return summary
    
    def get_metrics_by_name(
        self,
        metric_name: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PerformanceMetric]:
        """Получение метрик по названию"""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=1)
        
        filtered_metrics = [
            m for m in self.metrics
            if m.name == metric_name and m.timestamp > since
        ]
        
        return sorted(filtered_metrics, key=lambda x: x.timestamp, reverse=True)[:limit]


class PerformanceMiddleware:
    """Middleware для мониторинга производительности"""
    
    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
    
    async def __call__(self, request, call_next):
        """Обработка запроса с профилированием"""
        start_time = time.time()
        
        # Извлекаем информацию о запросе
        method = request.method
        path = request.url.path
        user_id = getattr(request.state, 'user', {}).get('user_id') if hasattr(request.state, 'user') else None
        
        # Размер запроса
        request_size = 0
        if hasattr(request, 'body'):
            try:
                body = await request.body()
                request_size = len(body)
            except:
                pass
        
        try:
            # Выполняем запрос
            response = await call_next(request)
            
            # Вычисляем время выполнения
            execution_time = time.time() - start_time
            
            # Размер ответа
            response_size = 0
            if hasattr(response, 'body'):
                response_size = len(getattr(response, 'body', b''))
            
            # Записываем метрики
            self.profiler.record_request(
                endpoint=path,
                method=method,
                response_time=execution_time,
                status_code=response.status_code,
                user_id=user_id,
                request_size=request_size,
                response_size=response_size
            )
            
            return response
            
        except Exception as e:
            # Записываем ошибку
            execution_time = time.time() - start_time
            self.profiler.record_request(
                endpoint=path,
                method=method,
                response_time=execution_time,
                status_code=500,
                user_id=user_id,
                request_size=request_size
            )
            
            # Записываем метрику ошибки
            self.profiler.record_metric("http_request_error", 1.0, "count", {
                "endpoint": path,
                "method": method,
                "error_type": type(e).__name__
            })
            
            raise


def performance_timer(metric_name: str):
    """Декоратор для измерения времени выполнения функций"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                profiler.record_metric(metric_name, execution_time, "seconds", {
                    "function": func.__name__,
                    "status": "success"
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                profiler.record_metric(metric_name, execution_time, "seconds", {
                    "function": func.__name__,
                    "status": "error",
                    "error_type": type(e).__name__
                })
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                profiler.record_metric(metric_name, execution_time, "seconds", {
                    "function": func.__name__,
                    "status": "success"
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                profiler.record_metric(metric_name, execution_time, "seconds", {
                    "function": func.__name__,
                    "status": "error", 
                    "error_type": type(e).__name__
                })
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class SystemMetricsCollector:
    """Сборщик системных метрик в фоне"""
    
    def __init__(self, profiler: PerformanceProfiler, interval: int = 60):
        self.profiler = profiler
        self.interval = interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Запуск сборщика"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.thread.start()
        logger.info("System metrics collector started")
    
    def stop(self):
        """Остановка сборщика"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("System metrics collector stopped")
    
    def _collect_loop(self):
        """Основной цикл сбора метрик"""
        while self.running:
            try:
                self.profiler.record_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Ошибка сбора системных метрик: {e}")
                time.sleep(self.interval)


# Глобальные экземпляры
profiler = PerformanceProfiler()
performance_middleware = PerformanceMiddleware(profiler)
metrics_collector = SystemMetricsCollector(profiler)
