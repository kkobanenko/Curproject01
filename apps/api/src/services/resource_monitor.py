"""
Сервис для мониторинга использования ресурсов
"""
import asyncio
import logging
import time
import psutil
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import clickhouse_connect
from ..settings.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ResourceThreshold:
    """Пороговые значения для ресурсов"""
    cpu_percent: float = 80.0
    memory_percent: float = 85.0
    disk_percent: float = 90.0
    network_mb_per_sec: float = 100.0
    active_connections: int = 1000
    queue_length: int = 100


@dataclass
class ResourceAlert:
    """Алерт о превышении ресурсов"""
    resource_type: str
    current_value: float
    threshold_value: float
    severity: str
    message: str
    timestamp: datetime


class ResourceMonitor:
    """Монитор использования ресурсов"""
    
    def __init__(self):
        self.clickhouse_client = None
        self._initialize_clickhouse()
        self.thresholds = ResourceThreshold()
        self.alert_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 20
        self.monitoring_interval = 10  # секунд
        self.is_monitoring = False
        
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
            logger.info("ClickHouse connection initialized for resource monitoring")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse for resource monitoring: {e}")
            self.clickhouse_client = None
    
    def get_cpu_usage(self) -> Dict[str, float]:
        """Получение информации об использовании CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Загрузка по ядрам
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            return {
                'total_percent': cpu_percent,
                'core_count': cpu_count,
                'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                'per_core_percent': cpu_per_core,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return {'total_percent': 0, 'core_count': 0, 'frequency_mhz': 0, 'per_core_percent': [], 'load_average': [0, 0, 0]}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании памяти"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total_mb': memory.total / (1024 * 1024),
                'available_mb': memory.available / (1024 * 1024),
                'used_mb': memory.used / (1024 * 1024),
                'percent': memory.percent,
                'swap_total_mb': swap.total / (1024 * 1024),
                'swap_used_mb': swap.used / (1024 * 1024),
                'swap_percent': swap.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {'total_mb': 0, 'available_mb': 0, 'used_mb': 0, 'percent': 0, 'swap_total_mb': 0, 'swap_used_mb': 0, 'swap_percent': 0}
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании диска"""
        try:
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Информация о всех дисках
            partitions = psutil.disk_partitions()
            disk_info = []
            
            for partition in partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total_gb': partition_usage.total / (1024 * 1024 * 1024),
                        'used_gb': partition_usage.used / (1024 * 1024 * 1024),
                        'free_gb': partition_usage.free / (1024 * 1024 * 1024),
                        'percent': (partition_usage.used / partition_usage.total) * 100
                    })
                except PermissionError:
                    continue
            
            return {
                'root_total_gb': disk_usage.total / (1024 * 1024 * 1024),
                'root_used_gb': disk_usage.used / (1024 * 1024 * 1024),
                'root_free_gb': disk_usage.free / (1024 * 1024 * 1024),
                'root_percent': (disk_usage.used / disk_usage.total) * 100,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'partitions': disk_info
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {'root_total_gb': 0, 'root_used_gb': 0, 'root_free_gb': 0, 'root_percent': 0, 'read_bytes': 0, 'write_bytes': 0, 'partitions': []}
    
    def get_network_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании сети"""
        try:
            network_io = psutil.net_io_counters()
            network_connections = psutil.net_connections()
            
            # Статистика по интерфейсам
            network_interfaces = psutil.net_if_stats()
            interface_info = []
            
            for interface, stats in network_interfaces.items():
                interface_info.append({
                    'name': interface,
                    'is_up': stats.isup,
                    'duplex': stats.duplex,
                    'speed_mbps': stats.speed,
                    'mtu': stats.mtu
                })
            
            return {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv,
                'active_connections': len(network_connections),
                'interfaces': interface_info
            }
        except Exception as e:
            logger.error(f"Error getting network usage: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0, 'active_connections': 0, 'interfaces': []}
    
    def get_process_info(self) -> Dict[str, Any]:
        """Получение информации о процессах"""
        try:
            current_process = psutil.Process()
            
            # Информация о текущем процессе
            process_info = {
                'pid': current_process.pid,
                'name': current_process.name(),
                'cpu_percent': current_process.cpu_percent(),
                'memory_mb': current_process.memory_info().rss / (1024 * 1024),
                'memory_percent': current_process.memory_percent(),
                'num_threads': current_process.num_threads(),
                'num_fds': current_process.num_fds() if hasattr(current_process, 'num_fds') else 0,
                'create_time': current_process.create_time()
            }
            
            # Топ процессов по использованию CPU
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    top_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Сортировка по CPU
            top_processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            
            return {
                'current_process': process_info,
                'top_processes': top_processes[:10],  # Топ 10
                'total_processes': len(list(psutil.process_iter()))
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {'current_process': {}, 'top_processes': [], 'total_processes': 0}
    
    def check_resource_thresholds(self, cpu_usage: Dict[str, float], 
                                memory_usage: Dict[str, Any],
                                disk_usage: Dict[str, Any],
                                network_usage: Dict[str, Any]) -> List[ResourceAlert]:
        """Проверка превышения пороговых значений ресурсов"""
        alerts = []
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Проверка CPU
            if cpu_usage['total_percent'] > self.thresholds.cpu_percent:
                alerts.append(ResourceAlert(
                    resource_type='cpu',
                    current_value=cpu_usage['total_percent'],
                    threshold_value=self.thresholds.cpu_percent,
                    severity='warning' if cpu_usage['total_percent'] < 95 else 'critical',
                    message=f"High CPU usage: {cpu_usage['total_percent']:.1f}%",
                    timestamp=timestamp
                ))
            
            # Проверка памяти
            if memory_usage['percent'] > self.thresholds.memory_percent:
                alerts.append(ResourceAlert(
                    resource_type='memory',
                    current_value=memory_usage['percent'],
                    threshold_value=self.thresholds.memory_percent,
                    severity='warning' if memory_usage['percent'] < 95 else 'critical',
                    message=f"High memory usage: {memory_usage['percent']:.1f}%",
                    timestamp=timestamp
                ))
            
            # Проверка диска
            if disk_usage['root_percent'] > self.thresholds.disk_percent:
                alerts.append(ResourceAlert(
                    resource_type='disk',
                    current_value=disk_usage['root_percent'],
                    threshold_value=self.thresholds.disk_percent,
                    severity='warning' if disk_usage['root_percent'] < 95 else 'critical',
                    message=f"High disk usage: {disk_usage['root_percent']:.1f}%",
                    timestamp=timestamp
                ))
            
            # Проверка сети (базовая проверка)
            network_mb_per_sec = (network_usage['bytes_sent'] + network_usage['bytes_recv']) / (1024 * 1024)
            if network_mb_per_sec > self.thresholds.network_mb_per_sec:
                alerts.append(ResourceAlert(
                    resource_type='network',
                    current_value=network_mb_per_sec,
                    threshold_value=self.thresholds.network_mb_per_sec,
                    severity='warning',
                    message=f"High network usage: {network_mb_per_sec:.1f} MB/s",
                    timestamp=timestamp
                ))
            
            # Проверка активных соединений
            if network_usage['active_connections'] > self.thresholds.active_connections:
                alerts.append(ResourceAlert(
                    resource_type='connections',
                    current_value=network_usage['active_connections'],
                    threshold_value=self.thresholds.active_connections,
                    severity='warning',
                    message=f"High number of connections: {network_usage['active_connections']}",
                    timestamp=timestamp
                ))
            
        except Exception as e:
            logger.error(f"Error checking resource thresholds: {e}")
        
        return alerts
    
    async def collect_resource_metrics(self, service_name: str = "api") -> Dict[str, Any]:
        """Сбор всех метрик ресурсов"""
        try:
            cpu_usage = self.get_cpu_usage()
            memory_usage = self.get_memory_usage()
            disk_usage = self.get_disk_usage()
            network_usage = self.get_network_usage()
            process_info = self.get_process_info()
            
            # Проверка пороговых значений
            alerts = self.check_resource_thresholds(cpu_usage, memory_usage, disk_usage, network_usage)
            
            # Сохранение алертов
            if alerts:
                await self._store_alerts(alerts, service_name)
            
            # Подготовка данных для сохранения
            resource_data = {
                'timestamp': datetime.now(timezone.utc),
                'service': service_name,
                'cpu_usage_percent': cpu_usage['total_percent'],
                'memory_usage_mb': memory_usage['used_mb'],
                'disk_usage_mb': disk_usage['root_used_gb'] * 1024,  # Конвертируем в MB
                'network_io_bytes': network_usage['bytes_sent'] + network_usage['bytes_recv'],
                'active_connections': network_usage['active_connections'],
                'queue_length': process_info['current_process'].get('num_threads', 0)
            }
            
            # Сохранение метрик ресурсов
            await self._store_resource_metrics(resource_data)
            
            return {
                'cpu': cpu_usage,
                'memory': memory_usage,
                'disk': disk_usage,
                'network': network_usage,
                'process': process_info,
                'alerts': [alert.__dict__ for alert in alerts]
            }
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            return {}
    
    async def _store_resource_metrics(self, resource_data: Dict[str, Any]):
        """Сохранение метрик ресурсов в ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            self.clickhouse_client.insert(
                'rag.resource_usage_metrics',
                [resource_data]
            )
        except Exception as e:
            logger.error(f"Error storing resource metrics: {e}")
    
    async def _store_alerts(self, alerts: List[ResourceAlert], service_name: str):
        """Сохранение алертов в ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            alert_data = []
            for alert in alerts:
                alert_data.append({
                    'timestamp': alert.timestamp,
                    'alert_id': f"{alert.resource_type}_{int(alert.timestamp.timestamp())}",
                    'alert_type': 'resource_threshold',
                    'severity': alert.severity,
                    'service': service_name,
                    'message': alert.message,
                    'status': 'active',
                    'resolved_at': None,
                    'metadata': {
                        'resource_type': alert.resource_type,
                        'current_value': str(alert.current_value),
                        'threshold_value': str(alert.threshold_value)
                    }
                })
            
            self.alert_buffer.extend(alert_data)
            
            # Записываем при достижении размера буфера
            if len(self.alert_buffer) >= self.buffer_size:
                await self._flush_alert_buffer()
                
        except Exception as e:
            logger.error(f"Error storing alerts: {e}")
    
    async def _flush_alert_buffer(self):
        """Сброс буфера алертов в ClickHouse"""
        if not self.alert_buffer:
            return
        
        try:
            self.clickhouse_client.insert(
                'rag.alerts',
                self.alert_buffer
            )
            self.alert_buffer.clear()
            logger.debug(f"Flushed {len(self.alert_buffer)} alerts to ClickHouse")
        except Exception as e:
            logger.error(f"Error flushing alert buffer: {e}")
    
    async def start_monitoring(self, service_name: str = "api"):
        """Запуск мониторинга ресурсов"""
        if self.is_monitoring:
            logger.warning("Resource monitoring is already running")
            return
        
        self.is_monitoring = True
        logger.info(f"Starting resource monitoring for service: {service_name}")
        
        while self.is_monitoring:
            try:
                await self.collect_resource_metrics(service_name)
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def stop_monitoring(self):
        """Остановка мониторинга ресурсов"""
        self.is_monitoring = False
        logger.info("Stopping resource monitoring")
        
        # Сброс оставшихся алертов
        if self.alert_buffer:
            await self._flush_alert_buffer()
    
    def update_thresholds(self, **kwargs):
        """Обновление пороговых значений"""
        for key, value in kwargs.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)
                logger.info(f"Updated threshold {key} to {value}")
    
    async def get_resource_statistics(self, service_name: str, hours: int = 24) -> Dict[str, Any]:
        """Получение статистики использования ресурсов"""
        if not self.clickhouse_client:
            return {}
        
        try:
            query = """
            SELECT 
                avg(cpu_usage_percent) as avg_cpu,
                max(cpu_usage_percent) as max_cpu,
                avg(memory_usage_mb) as avg_memory,
                max(memory_usage_mb) as max_memory,
                avg(disk_usage_mb) as avg_disk,
                max(disk_usage_mb) as max_disk,
                avg(active_connections) as avg_connections,
                max(active_connections) as max_connections
            FROM rag.resource_usage_metrics
            WHERE service = %(service_name)s 
            AND timestamp >= now() - INTERVAL %(hours)s HOUR
            """
            
            result = self.clickhouse_client.query(
                query,
                parameters={'service_name': service_name, 'hours': hours}
            )
            
            if result.result_rows:
                row = result.result_rows[0]
                return {
                    'avg_cpu': float(row[0]) if row[0] else 0.0,
                    'max_cpu': float(row[1]) if row[1] else 0.0,
                    'avg_memory': float(row[2]) if row[2] else 0.0,
                    'max_memory': float(row[3]) if row[3] else 0.0,
                    'avg_disk': float(row[4]) if row[4] else 0.0,
                    'max_disk': float(row[5]) if row[5] else 0.0,
                    'avg_connections': float(row[6]) if row[6] else 0.0,
                    'max_connections': float(row[7]) if row[7] else 0.0
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting resource statistics: {e}")
            return {}


# Глобальный экземпляр монитора ресурсов
resource_monitor = ResourceMonitor()


def get_resource_monitor() -> ResourceMonitor:
    """Получение экземпляра монитора ресурсов"""
    return resource_monitor
