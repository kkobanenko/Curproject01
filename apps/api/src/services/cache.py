"""
Расширенная система кэширования с Redis для оптимизации производительности
"""
import json
import pickle
import hashlib
from typing import Any, Optional, Union, List, Dict, Callable
from datetime import datetime, timedelta
import asyncio
import logging
from functools import wraps, lru_cache
import redis.asyncio as redis

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheKeyBuilder:
    """Строитель ключей кэша"""
    
    @staticmethod
    def user_key(user_id: int) -> str:
        """Ключ для данных пользователя"""
        return f"user:{user_id}"
    
    @staticmethod
    def document_key(document_id: str) -> str:
        """Ключ для данных документа"""
        return f"document:{document_id}"
    
    @staticmethod
    def search_key(query: str, filters: Dict[str, Any], user_id: int) -> str:
        """Ключ для результатов поиска"""
        filter_hash = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()[:8]
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"search:{user_id}:{query_hash}:{filter_hash}"
    
    @staticmethod
    def rag_key(question: str, context_ids: List[str], user_id: int) -> str:
        """Ключ для RAG ответов"""
        context_hash = hashlib.md5(json.dumps(sorted(context_ids)).encode()).hexdigest()[:8]
        question_hash = hashlib.md5(question.encode()).hexdigest()[:8]
        return f"rag:{user_id}:{question_hash}:{context_hash}"
    
    @staticmethod
    def embeddings_key(text: str, model: str) -> str:
        """Ключ для эмбеддингов"""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"embeddings:{model}:{text_hash}"
    
    @staticmethod
    def metrics_key(metric_type: str, period: str, timestamp: str) -> str:
        """Ключ для метрик"""
        return f"metrics:{metric_type}:{period}:{timestamp}"
    
    @staticmethod
    def api_response_key(endpoint: str, params: Dict[str, Any], user_id: int) -> str:
        """Ключ для ответов API"""
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        return f"api:{endpoint}:{user_id}:{params_hash}"


class RedisCacheService:
    """Сервис кэширования с Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.default_ttl = 3600  # 1 час по умолчанию
        self.max_retries = 3
        
        # Конфигурация TTL для разных типов данных
        self.ttl_config = {
            "user": 1800,           # 30 минут
            "document": 7200,       # 2 часа
            "search": 600,          # 10 минут
            "rag": 1800,           # 30 минут
            "embeddings": 86400,    # 24 часа
            "metrics": 300,         # 5 минут
            "api": 60,             # 1 минута
            "session": 3600,       # 1 час
        }
    
    async def initialize(self):
        """Инициализация подключения к Redis"""
        try:
            self.connection_pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                encoding="utf-8",
                decode_responses=False,  # Для работы с pickle
                max_connections=20,
                retry_on_timeout=True,
                retry_on_error=[redis.BusyLoadingError, redis.ConnectionError],
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Тестируем подключение
            await self.redis_client.ping()
            logger.info("Redis cache service инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Redis: {e}")
            self.redis_client = None
    
    async def close(self):
        """Закрытие подключения"""
        if self.redis_client:
            await self.redis_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
    
    def _get_ttl(self, key_type: str) -> int:
        """Получение TTL для типа ключа"""
        return self.ttl_config.get(key_type, self.default_ttl)
    
    def _extract_key_type(self, key: str) -> str:
        """Извлечение типа ключа"""
        return key.split(":", 1)[0] if ":" in key else "default"
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Сохранение данных в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни в секундах
            serialize: Сериализовать ли значение
        """
        if not self.redis_client:
            return False
        
        try:
            # Определяем TTL
            if ttl is None:
                key_type = self._extract_key_type(key)
                ttl = self._get_ttl(key_type)
            
            # Сериализация данных
            if serialize:
                if isinstance(value, (dict, list)):
                    serialized_value = json.dumps(value, default=str).encode()
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = value
            
            # Сохранение с TTL
            await self.redis_client.setex(key, ttl, serialized_value)
            
            logger.debug(f"Cached key: {key}, TTL: {ttl}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в кэш {key}: {e}")
            return False
    
    async def get(
        self,
        key: str,
        deserialize: bool = True,
        default: Any = None
    ) -> Any:
        """
        Получение данных из кэша
        
        Args:
            key: Ключ кэша
            deserialize: Десериализовать ли значение
            default: Значение по умолчанию
        """
        if not self.redis_client:
            return default
        
        try:
            cached_value = await self.redis_client.get(key)
            
            if cached_value is None:
                return default
            
            # Десериализация
            if deserialize:
                try:
                    # Пробуем JSON
                    return json.loads(cached_value.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        # Пробуем pickle
                        return pickle.loads(cached_value)
                    except pickle.PickleError:
                        # Возвращаем как есть
                        return cached_value
            else:
                return cached_value
                
        except Exception as e:
            logger.error(f"Ошибка получения из кэша {key}: {e}")
            return default
    
    async def delete(self, key: str) -> bool:
        """Удаление ключа из кэша"""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Ошибка удаления из кэша {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Удаление ключей по паттерну"""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Ошибка удаления по паттерну {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        if not self.redis_client:
            return False
        
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Ошибка проверки существования {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Получение TTL ключа"""
        if not self.redis_client:
            return -1
        
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Ошибка получения TTL {key}: {e}")
            return -1
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Установка TTL для ключа"""
        if not self.redis_client:
            return False
        
        try:
            return bool(await self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Ошибка установки TTL {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Инкремент числового значения"""
        if not self.redis_client:
            return 0
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Ошибка инкремента {key}: {e}")
            return 0
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании памяти"""
        if not self.redis_client:
            return {}
        
        try:
            info = await self.redis_client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "total_system_memory": info.get("total_system_memory", 0),
                "memory_usage_percentage": round(
                    (info.get("used_memory", 0) / info.get("total_system_memory", 1)) * 100, 2
                )
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики памяти: {e}")
            return {}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение общей статистики кэша"""
        if not self.redis_client:
            return {}
        
        try:
            info = await self.redis_client.info()
            return {
                "total_keys": info.get("db0", {}).get("keys", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2
                ),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}


class CacheManager:
    """Менеджер кэширования с высокоуровневыми операциями"""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.local_cache = {}  # L1 кэш в памяти
        self.local_cache_size = 1000
        self.local_cache_ttl = 60  # 1 минута для L1
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
        use_local_cache: bool = True
    ) -> Any:
        """
        Получение данных из кэша или создание через factory функцию
        
        Args:
            key: Ключ кэша
            factory: Функция для создания данных если нет в кэше
            ttl: TTL для сохранения
            use_local_cache: Использовать ли локальный кэш
        """
        # Проверяем локальный кэш
        if use_local_cache and key in self.local_cache:
            local_entry = self.local_cache[key]
            if datetime.utcnow() < local_entry["expires_at"]:
                return local_entry["data"]
            else:
                del self.local_cache[key]
        
        # Проверяем Redis кэш
        cached_value = await self.cache.get(key)
        if cached_value is not None:
            # Сохраняем в локальный кэш
            if use_local_cache:
                self._set_local_cache(key, cached_value)
            return cached_value
        
        # Создаем данные через factory
        try:
            if asyncio.iscoroutinefunction(factory):
                data = await factory()
            else:
                data = factory()
            
            # Сохраняем в Redis
            await self.cache.set(key, data, ttl)
            
            # Сохраняем в локальный кэш
            if use_local_cache:
                self._set_local_cache(key, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка factory функции для ключа {key}: {e}")
            return None
    
    def _set_local_cache(self, key: str, data: Any):
        """Сохранение в локальный кэш"""
        # Ограничиваем размер локального кэша
        if len(self.local_cache) >= self.local_cache_size:
            # Удаляем самые старые записи
            old_keys = sorted(
                self.local_cache.keys(),
                key=lambda k: self.local_cache[k]["created_at"]
            )[:100]  # Удаляем 100 старых записей
            
            for old_key in old_keys:
                del self.local_cache[old_key]
        
        # Добавляем новую запись
        self.local_cache[key] = {
            "data": data,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.local_cache_ttl)
        }
    
    async def invalidate_user_cache(self, user_id: int):
        """Инвалидация всего кэша пользователя"""
        patterns = [
            f"user:{user_id}*",
            f"search:{user_id}:*",
            f"rag:{user_id}:*",
            f"api:*:{user_id}:*"
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
        
        logger.info(f"Invalidated cache for user {user_id}")
    
    async def invalidate_document_cache(self, document_id: str):
        """Инвалидация кэша документа"""
        patterns = [
            f"document:{document_id}*",
            f"search:*",  # Поиск может включать этот документ
            f"rag:*"      # RAG ответы могут использовать этот документ
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
        
        logger.info(f"Invalidated cache for document {document_id}")
    
    async def warm_up_cache(self, user_id: int):
        """Предварительное заполнение кэша"""
        try:
            # Предзагружаем часто используемые данные
            user_key = CacheKeyBuilder.user_key(user_id)
            
            # TODO: Загрузить данные пользователя
            # TODO: Загрузить популярные документы
            # TODO: Предвычислить часто используемые метрики
            
            logger.info(f"Cache warmed up for user {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка предварительного заполнения кэша для пользователя {user_id}: {e}")


def cached(
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    use_local_cache: bool = True
):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        ttl: Время жизни кэша
        key_builder: Функция для построения ключа кэша
        use_local_cache: Использовать ли локальный кэш
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Строим ключ кэша
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Автоматическое построение ключа
                func_name = func.__name__
                args_str = str(args) + str(sorted(kwargs.items()))
                key_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"func:{func_name}:{key_hash}"
            
            # Получаем из кэша или выполняем функцию
            result = await cache_manager.get_or_set(
                key=cache_key,
                factory=lambda: func(*args, **kwargs),
                ttl=ttl,
                use_local_cache=use_local_cache
            )
            
            return result
        
        return wrapper
    return decorator


# Глобальные экземпляры
cache_service = RedisCacheService()
cache_manager = CacheManager(cache_service)