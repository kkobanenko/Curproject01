"""
Сервис кэширования с Redis
"""
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import logging
import redis.asyncio as redis
from fastapi import HTTPException

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    """Сервис для работы с кэшем Redis"""
    
    def __init__(self):
        """Инициализация подключения к Redis"""
        self.redis_client = None
        self.default_ttl = 3600  # 1 час по умолчанию
        
    async def connect(self):
        """Подключение к Redis"""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=False,  # Для поддержки pickle
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Проверяем подключение
            await self.redis_client.ping()
            logger.info("✅ Подключение к Redis установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 Отключение от Redis")
    
    async def is_connected(self) -> bool:
        """Проверка подключения к Redis"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except:
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения из кэша
        
        Args:
            key: Ключ кэша
            default: Значение по умолчанию
            
        Returns:
            Значение из кэша или default
        """
        if not await self.is_connected():
            return default
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return default
            
            # Пробуем десериализовать как JSON
            try:
                return json.loads(value.decode('utf-8'))
            except:
                # Если не JSON, пробуем pickle
                try:
                    return pickle.loads(value)
                except:
                    # Если не pickle, возвращаем как строку
                    return value.decode('utf-8')
                    
        except Exception as e:
            logger.error(f"Ошибка получения из кэша {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Установка значения в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для кэширования
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно, False иначе
        """
        if not await self.is_connected():
            return False
        
        try:
            ttl = ttl or self.default_ttl
            
            # Пробуем сериализовать как JSON
            try:
                serialized_value = json.dumps(value, ensure_ascii=False)
            except:
                # Если не JSON, используем pickle
                serialized_value = pickle.dumps(value)
            
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки в кэш {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Удаление ключа из кэша
        
        Args:
            key: Ключ для удаления
            
        Returns:
            True если успешно, False иначе
        """
        if not await self.is_connected():
            return False
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Ошибка удаления из кэша {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Проверка существования ключа
        
        Args:
            key: Ключ для проверки
            
        Returns:
            True если ключ существует, False иначе
        """
        if not await self.is_connected():
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки существования ключа {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Установка времени жизни для ключа
        
        Args:
            key: Ключ
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно, False иначе
        """
        if not await self.is_connected():
            return False
        
        try:
            return await self.redis_client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Ошибка установки TTL для ключа {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Увеличение числового значения
        
        Args:
            key: Ключ
            amount: Количество для увеличения
            
        Returns:
            Новое значение или None при ошибке
        """
        if not await self.is_connected():
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Ошибка увеличения значения для ключа {key}: {e}")
            return None
    
    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Получение нескольких значений по ключам
        
        Args:
            keys: Список ключей
            
        Returns:
            Словарь {ключ: значение}
        """
        if not await self.is_connected():
            return {}
        
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value.decode('utf-8'))
                    except:
                        try:
                            result[key] = pickle.loads(value)
                        except:
                            result[key] = value.decode('utf-8')
                else:
                    result[key] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения множества значений: {e}")
            return {}
    
    async def set_many(self, data: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Установка нескольких значений
        
        Args:
            data: Словарь {ключ: значение}
            ttl: Время жизни в секундах
            
        Returns:
            True если успешно, False иначе
        """
        if not await self.is_connected():
            return False
        
        try:
            ttl = ttl or self.default_ttl
            pipeline = self.redis_client.pipeline()
            
            for key, value in data.items():
                try:
                    serialized_value = json.dumps(value, ensure_ascii=False)
                except:
                    serialized_value = pickle.dumps(value)
                
                pipeline.setex(key, ttl, serialized_value)
            
            await pipeline.execute()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки множества значений: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Очистка ключей по паттерну
        
        Args:
            pattern: Паттерн для поиска ключей (например, "user:*")
            
        Returns:
            Количество удаленных ключей
        """
        if not await self.is_connected():
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                return len(keys)
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка очистки по паттерну {pattern}: {e}")
            return 0
    
    async def get_stats(self) -> dict[str, Any]:
        """
        Получение статистики Redis
        
        Returns:
            Словарь со статистикой
        """
        if not await self.is_connected():
            return {"error": "Redis не подключен"}
        
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики Redis: {e}")
            return {"error": str(e)}


# Глобальный экземпляр сервиса кэширования
cache_service = CacheService()
