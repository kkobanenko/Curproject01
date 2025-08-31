"""
Сервис для сбора метрик производительности системы
"""
import asyncio
import psutil
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import clickhouse_connect
from ..settings.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SystemMetric:
    """Структура для метрики системы"""
    name: str
    value: float
    unit: str
    tags: Dict[str, str]


@dataclass
class ResourceUsage:
    """Структура для использования ресурсов"""
    cpu_percent: float
    memory_mb: int
    disk_mb: int
    network_io_bytes: int
    active_connections: int
    queue_length: int


class MetricsCollector:
    """Коллектор метрик производительности"""
    
    def __init__(self):
        self.clickhouse_client = None
        self._initialize_clickhouse()
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 100
        self.collection_interval = 30  # секунд
        
    def _initialize_clickhouse(self):
        """Инициализация подключения к ClickHouse"""
        try:
            self.clickhouse_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DATABASE
            )
            logger.info("ClickHouse connection initialized for metrics")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse: {e}")
            self.clickhouse_client = None
    
    async def collect_system_metrics(self, service_name: str) -> List[SystemMetric]:
        """Сбор системных метрик"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        try:
            # CPU метрики
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(SystemMetric(
                name="cpu_usage_percent",
                value=cpu_percent,
                unit="percent",
                tags={"service": service_name, "type": "system"}
            ))
            
            # Memory метрики
            memory = psutil.virtual_memory()
            metrics.append(SystemMetric(
                name="memory_usage_percent",
                value=memory.percent,
                unit="percent",
                tags={"service": service_name, "type": "system"}
            ))
            
            metrics.append(SystemMetric(
                name="memory_available_mb",
                value=memory.available / (1024 * 1024),
                unit="MB",
                tags={"service": service_name, "type": "system"}
            ))
            
            # Disk метрики
            disk = psutil.disk_usage('/')
            metrics.append(SystemMetric(
                name="disk_usage_percent",
                value=(disk.used / disk.total) * 100,
                unit="percent",
                tags={"service": service_name, "type": "system"}
            ))
            
            metrics.append(SystemMetric(
                name="disk_free_gb",
                value=disk.free / (1024 * 1024 * 1024),
                unit="GB",
                tags={"service": service_name, "type": "system"}
            ))
            
            # Network метрики
            network = psutil.net_io_counters()
            metrics.append(SystemMetric(
                name="network_bytes_sent",
                value=network.bytes_sent,
                unit="bytes",
                tags={"service": service_name, "type": "network"}
            ))
            
            metrics.append(SystemMetric(
                name="network_bytes_recv",
                value=network.bytes_recv,
                unit="bytes",
                tags={"service": service_name, "type": "network"}
            ))
            
            # Process метрики
            process = psutil.Process()
            metrics.append(SystemMetric(
                name="process_cpu_percent",
                value=process.cpu_percent(),
                unit="percent",
                tags={"service": service_name, "type": "process"}
            ))
            
            metrics.append(SystemMetric(
                name="process_memory_mb",
                value=process.memory_info().rss / (1024 * 1024),
                unit="MB",
                tags={"service": service_name, "type": "process"}
            ))
            
            metrics.append(SystemMetric(
                name="process_threads",
                value=process.num_threads(),
                unit="count",
                tags={"service": service_name, "type": "process"}
            ))
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            
        return metrics
    
    async def collect_resource_usage(self, service_name: str) -> ResourceUsage:
        """Сбор метрик использования ресурсов"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Подсчет активных соединений (примерная оценка)
            active_connections = len(psutil.net_connections())
            
            # Подсчет длины очереди (примерная оценка)
            queue_length = len(asyncio.all_tasks())
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=int(memory.used / (1024 * 1024)),
                disk_mb=int(disk.used / (1024 * 1024)),
                network_io_bytes=network.bytes_sent + network.bytes_recv,
                active_connections=active_connections,
                queue_length=queue_length
            )
        except Exception as e:
            logger.error(f"Error collecting resource usage: {e}")
            return ResourceUsage(0, 0, 0, 0, 0, 0)
    
    async def collect_application_metrics(self, service_name: str) -> List[SystemMetric]:
        """Сбор метрик приложения"""
        metrics = []
        
        try:
            # Метрики FastAPI
            from fastapi import Request
            # Здесь можно добавить метрики из FastAPI middleware
            
            # Метрики базы данных
            if hasattr(settings, 'DATABASE_URL'):
                metrics.append(SystemMetric(
                    name="database_connections_active",
                    value=0,  # Заглушка, нужно реализовать подсчет
                    unit="count",
                    tags={"service": service_name, "type": "database"}
                ))
            
            # Метрики кэша
            if hasattr(settings, 'REDIS_URL'):
                metrics.append(SystemMetric(
                    name="cache_hit_rate",
                    value=0,  # Заглушка, нужно реализовать подсчет
                    unit="percent",
                    tags={"service": service_name, "type": "cache"}
                ))
            
            # Метрики эмбеддингов
            metrics.append(SystemMetric(
                name="embedding_requests_per_minute",
                value=0,  # Заглушка, нужно реализовать подсчет
                unit="count",
                tags={"service": service_name, "type": "embedding"}
            ))
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            
        return metrics
    
    def _prepare_metric_data(self, metrics: List[SystemMetric]) -> List[Dict[str, Any]]:
        """Подготовка данных метрик для записи в ClickHouse"""
        data = []
        timestamp = datetime.now(timezone.utc)
        
        for metric in metrics:
            data.append({
                'timestamp': timestamp,
                'service': metric.tags.get('service', 'unknown'),
                'metric_name': metric.name,
                'metric_value': metric.value,
                'metric_unit': metric.unit,
                'tags': metric.tags
            })
        
        return data
    
    def _prepare_resource_data(self, resource_usage: ResourceUsage, service_name: str) -> Dict[str, Any]:
        """Подготовка данных использования ресурсов"""
        return {
            'timestamp': datetime.now(timezone.utc),
            'service': service_name,
            'cpu_usage_percent': resource_usage.cpu_percent,
            'memory_usage_mb': resource_usage.memory_mb,
            'disk_usage_mb': resource_usage.disk_mb,
            'network_io_bytes': resource_usage.network_io_bytes,
            'active_connections': resource_usage.active_connections,
            'queue_length': resource_usage.queue_length
        }
    
    async def store_metrics(self, metrics: List[SystemMetric]):
        """Сохранение метрик в ClickHouse"""
        if not self.clickhouse_client:
            logger.warning("ClickHouse client not available, skipping metrics storage")
            return
        
        try:
            data = self._prepare_metric_data(metrics)
            self.metrics_buffer.extend(data)
            
            # Записываем в базу при достижении размера буфера
            if len(self.metrics_buffer) >= self.buffer_size:
                await self._flush_buffer()
                
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def store_resource_usage(self, resource_usage: ResourceUsage, service_name: str):
        """Сохранение метрик использования ресурсов"""
        if not self.clickhouse_client:
            logger.warning("ClickHouse client not available, skipping resource usage storage")
            return
        
        try:
            data = self._prepare_resource_data(resource_usage, service_name)
            
            self.clickhouse_client.insert(
                'rag.resource_usage_metrics',
                [data]
            )
            
        except Exception as e:
            logger.error(f"Error storing resource usage: {e}")
    
    async def _flush_buffer(self):
        """Сброс буфера метрик в ClickHouse"""
        if not self.metrics_buffer:
            return
        
        try:
            self.clickhouse_client.insert(
                'rag.system_metrics',
                self.metrics_buffer
            )
            self.metrics_buffer.clear()
            logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to ClickHouse")
        except Exception as e:
            logger.error(f"Error flushing metrics buffer: {e}")
    
    async def start_collection(self, service_name: str = "api"):
        """Запуск сбора метрик"""
        logger.info(f"Starting metrics collection for service: {service_name}")
        
        while True:
            try:
                # Сбор системных метрик
                system_metrics = await self.collect_system_metrics(service_name)
                await self.store_metrics(system_metrics)
                
                # Сбор метрик использования ресурсов
                resource_usage = await self.collect_resource_usage(service_name)
                await self.store_resource_usage(resource_usage, service_name)
                
                # Сбор метрик приложения
                app_metrics = await self.collect_application_metrics(service_name)
                await self.store_metrics(app_metrics)
                
                # Сброс буфера если есть данные
                if self.metrics_buffer:
                    await self._flush_buffer()
                
                # Ожидание до следующего сбора
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def stop_collection(self):
        """Остановка сбора метрик"""
        logger.info("Stopping metrics collection")
        
        # Сброс оставшихся метрик
        if self.metrics_buffer:
            await self._flush_buffer()
        
        # Закрытие соединения с ClickHouse
        if self.clickhouse_client:
            self.clickhouse_client.close()


# Глобальный экземпляр коллектора
metrics_collector = MetricsCollector()


async def start_metrics_collection(service_name: str = "api"):
    """Запуск сбора метрик (для использования в приложении)"""
    await metrics_collector.start_collection(service_name)


async def stop_metrics_collection():
    """Остановка сбора метрик"""
    await metrics_collector.stop_collection()


def get_metrics_collector() -> MetricsCollector:
    """Получение экземпляра коллектора метрик"""
    return metrics_collector
