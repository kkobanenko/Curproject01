"""
Система оптимизации базы данных и производительности запросов
"""
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import asyncio
import asyncpg
import psutil
from dataclasses import dataclass

from ..settings import get_settings
from .cache import cache_service, CacheKeyBuilder

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QueryStats:
    """Статистика выполнения запроса"""
    query_hash: str
    execution_time: float
    rows_returned: int
    query_text: str
    timestamp: datetime
    user_id: Optional[int] = None
    endpoint: Optional[str] = None


@dataclass
class IndexRecommendation:
    """Рекомендация по индексу"""
    table_name: str
    columns: List[str]
    index_type: str
    reason: str
    estimated_benefit: str
    priority: int


class DatabaseProfiler:
    """Профилировщик запросов к базе данных"""
    
    def __init__(self):
        self.query_stats: List[QueryStats] = []
        self.slow_query_threshold = 1.0  # 1 секунда
        self.max_stats_entries = 10000
        
    def record_query(
        self,
        query: str,
        execution_time: float,
        rows_returned: int = 0,
        user_id: Optional[int] = None,
        endpoint: Optional[str] = None
    ):
        """Запись статистики запроса"""
        import hashlib
        
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
        
        stats = QueryStats(
            query_hash=query_hash,
            execution_time=execution_time,
            rows_returned=rows_returned,
            query_text=query[:500],  # Ограничиваем длину
            timestamp=datetime.utcnow(),
            user_id=user_id,
            endpoint=endpoint
        )
        
        self.query_stats.append(stats)
        
        # Ограничиваем количество записей
        if len(self.query_stats) > self.max_stats_entries:
            self.query_stats = self.query_stats[-self.max_stats_entries:]
        
        # Логируем медленные запросы
        if execution_time > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected: {execution_time:.3f}s, "
                f"rows: {rows_returned}, hash: {query_hash}"
            )
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryStats]:
        """Получение самых медленных запросов"""
        return sorted(
            self.query_stats,
            key=lambda x: x.execution_time,
            reverse=True
        )[:limit]
    
    def get_frequent_queries(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """Получение самых частых запросов"""
        query_counts = {}
        query_times = {}
        
        for stat in self.query_stats:
            if stat.query_hash not in query_counts:
                query_counts[stat.query_hash] = 0
                query_times[stat.query_hash] = []
            
            query_counts[stat.query_hash] += 1
            query_times[stat.query_hash].append(stat.execution_time)
        
        # Сортируем по частоте
        frequent = []
        for query_hash, count in sorted(query_counts.items(), key=lambda x: x[1], reverse=True):
            avg_time = sum(query_times[query_hash]) / len(query_times[query_hash])
            frequent.append((query_hash, count, avg_time))
        
        return frequent[:limit]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Сводка производительности"""
        if not self.query_stats:
            return {}
        
        recent_stats = [
            s for s in self.query_stats 
            if s.timestamp > datetime.utcnow() - timedelta(hours=1)
        ]
        
        if not recent_stats:
            return {}
        
        execution_times = [s.execution_time for s in recent_stats]
        
        return {
            "total_queries": len(recent_stats),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "min_execution_time": min(execution_times),
            "slow_queries_count": len([s for s in recent_stats if s.execution_time > self.slow_query_threshold]),
            "queries_per_minute": len(recent_stats) / 60,
            "total_rows_returned": sum(s.rows_returned for s in recent_stats)
        }


class DatabaseOptimizer:
    """Оптимизатор базы данных"""
    
    def __init__(self):
        self.profiler = DatabaseProfiler()
        self.connection_pool = None
        
    async def initialize(self):
        """Инициализация подключения к БД"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database optimizer инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации оптимизатора БД: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Получение подключения с профилированием"""
        if not self.connection_pool:
            raise RuntimeError("Database optimizer не инициализирован")
        
        async with self.connection_pool.acquire() as connection:
            # Обертка для профилирования запросов
            original_execute = connection.execute
            original_fetch = connection.fetch
            original_fetchrow = connection.fetchrow
            
            async def profiled_execute(query, *args, **kwargs):
                start_time = time.time()
                try:
                    result = await original_execute(query, *args, **kwargs)
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time)
                    raise
            
            async def profiled_fetch(query, *args, **kwargs):
                start_time = time.time()
                try:
                    result = await original_fetch(query, *args, **kwargs)
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time, len(result))
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time)
                    raise
            
            async def profiled_fetchrow(query, *args, **kwargs):
                start_time = time.time()
                try:
                    result = await original_fetchrow(query, *args, **kwargs)
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time, 1 if result else 0)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.profiler.record_query(query, execution_time)
                    raise
            
            # Подменяем методы
            connection.execute = profiled_execute
            connection.fetch = profiled_fetch
            connection.fetchrow = profiled_fetchrow
            
            yield connection
    
    async def analyze_table_usage(self) -> Dict[str, Any]:
        """Анализ использования таблиц"""
        if not self.connection_pool:
            return {}
        
        query = """
        SELECT 
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            n_live_tup,
            n_dead_tup
        FROM pg_stat_user_tables
        ORDER BY seq_scan + idx_scan DESC
        """
        
        async with self.connection_pool.acquire() as conn:
            try:
                rows = await conn.fetch(query)
                return {
                    "tables": [dict(row) for row in rows],
                    "total_tables": len(rows),
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Ошибка анализа таблиц: {e}")
                return {}
    
    async def analyze_index_usage(self) -> Dict[str, Any]:
        """Анализ использования индексов"""
        if not self.connection_pool:
            return {}
        
        query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
        """
        
        async with self.connection_pool.acquire() as conn:
            try:
                rows = await conn.fetch(query)
                return {
                    "indexes": [dict(row) for row in rows],
                    "total_indexes": len(rows),
                    "unused_indexes": len([r for r in rows if r['idx_scan'] == 0]),
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Ошибка анализа индексов: {e}")
                return {}
    
    async def get_database_size_info(self) -> Dict[str, Any]:
        """Информация о размере базы данных"""
        if not self.connection_pool:
            return {}
        
        queries = {
            "database_size": "SELECT pg_size_pretty(pg_database_size(current_database()))",
            "largest_tables": """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY size_bytes DESC 
                LIMIT 10
            """
        }
        
        async with self.connection_pool.acquire() as conn:
            try:
                result = {}
                
                # Размер БД
                db_size = await conn.fetchval(queries["database_size"])
                result["database_size"] = db_size
                
                # Крупнейшие таблицы
                tables = await conn.fetch(queries["largest_tables"])
                result["largest_tables"] = [dict(row) for row in tables]
                
                return result
                
            except Exception as e:
                logger.error(f"Ошибка получения размеров БД: {e}")
                return {}
    
    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Генерация рекомендаций по индексам"""
        recommendations = []
        
        # Анализируем медленные запросы
        slow_queries = self.profiler.get_slow_queries(20)
        
        for query_stat in slow_queries:
            query = query_stat.query_text.lower()
            
            # Простые эвристики для рекомендаций
            if "where" in query and "order by" in query:
                recommendations.append(IndexRecommendation(
                    table_name="documents",  # Пример
                    columns=["created_at", "user_id"],
                    index_type="btree",
                    reason=f"Частый запрос с WHERE и ORDER BY (время: {query_stat.execution_time:.3f}s)",
                    estimated_benefit="Высокий",
                    priority=1
                ))
            
            if "join" in query:
                recommendations.append(IndexRecommendation(
                    table_name="document_chunks",
                    columns=["document_id"],
                    index_type="btree", 
                    reason=f"JOIN запрос без индекса (время: {query_stat.execution_time:.3f}s)",
                    estimated_benefit="Средний",
                    priority=2
                ))
        
        # Анализируем частые запросы
        frequent_queries = self.profiler.get_frequent_queries(10)
        
        for query_hash, count, avg_time in frequent_queries:
            if avg_time > 0.5 and count > 10:  # Частые и медленные
                recommendations.append(IndexRecommendation(
                    table_name="search_queries",
                    columns=["user_id", "created_at"],
                    index_type="btree",
                    reason=f"Частый запрос ({count} раз, ср. время: {avg_time:.3f}s)",
                    estimated_benefit="Высокий",
                    priority=1
                ))
        
        return sorted(recommendations, key=lambda x: x.priority)
    
    async def optimize_queries(self) -> Dict[str, Any]:
        """Автоматическая оптимизация запросов"""
        if not self.connection_pool:
            return {}
        
        optimizations = []
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Обновляем статистику таблиц
                await conn.execute("ANALYZE")
                optimizations.append("Updated table statistics")
                
                # Очищаем неиспользуемые подключения
                await conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < NOW() - INTERVAL '1 hour'")
                
                # Переиндексируем часто используемые таблицы
                tables_to_reindex = ["documents", "document_chunks", "users"]
                for table in tables_to_reindex:
                    try:
                        await conn.execute(f"REINDEX TABLE {table}")
                        optimizations.append(f"Reindexed table: {table}")
                    except Exception as e:
                        logger.warning(f"Не удалось переиндексировать {table}: {e}")
                
                return {
                    "optimizations_applied": optimizations,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "success"
                }
                
            except Exception as e:
                logger.error(f"Ошибка оптимизации: {e}")
                return {
                    "optimizations_applied": optimizations,
                    "error": str(e),
                    "status": "partial_failure"
                }
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Статистика подключений к БД"""
        if not self.connection_pool:
            return {}
        
        query = """
        SELECT 
            state,
            COUNT(*) as count,
            MAX(EXTRACT(EPOCH FROM (NOW() - state_change))) as max_duration
        FROM pg_stat_activity 
        WHERE datname = current_database()
        GROUP BY state
        """
        
        async with self.connection_pool.acquire() as conn:
            try:
                rows = await conn.fetch(query)
                
                stats = {
                    "pool_size": self.connection_pool.get_size(),
                    "pool_free": len(self.connection_pool._holders),
                    "connections_by_state": {row['state']: row['count'] for row in rows},
                    "analyzed_at": datetime.utcnow().isoformat()
                }
                
                return stats
                
            except Exception as e:
                logger.error(f"Ошибка получения статистики подключений: {e}")
                return {}


class SystemMonitor:
    """Монитор системных ресурсов"""
    
    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Получение системных метрик"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Память
            memory = psutil.virtual_memory()
            
            # Диск
            disk = psutil.disk_usage('/')
            
            # Сеть
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения системных метрик: {e}")
            return {}
    
    @staticmethod
    async def get_performance_recommendations() -> List[str]:
        """Рекомендации по производительности системы"""
        recommendations = []
        
        try:
            metrics = SystemMonitor.get_system_metrics()
            
            # Проверяем CPU
            if metrics.get("cpu", {}).get("percent", 0) > 80:
                recommendations.append("High CPU usage detected. Consider scaling horizontally or optimizing CPU-intensive operations.")
            
            # Проверяем память
            memory_percent = metrics.get("memory", {}).get("percent", 0)
            if memory_percent > 85:
                recommendations.append("High memory usage detected. Consider increasing RAM or optimizing memory usage.")
            elif memory_percent > 70:
                recommendations.append("Moderate memory usage. Monitor for potential memory leaks.")
            
            # Проверяем диск
            disk_percent = metrics.get("disk", {}).get("percent", 0)
            if disk_percent > 90:
                recommendations.append("Critical disk space. Clean up logs and temporary files immediately.")
            elif disk_percent > 80:
                recommendations.append("Low disk space. Consider cleanup or storage expansion.")
            
            # Общие рекомендации
            if not recommendations:
                recommendations.append("System performance is optimal.")
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            recommendations.append("Unable to analyze system performance.")
        
        return recommendations


# Глобальный экземпляр
db_optimizer = DatabaseOptimizer()
