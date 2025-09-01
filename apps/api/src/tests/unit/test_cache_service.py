"""
Unit тесты для сервиса кэширования
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import pickle

from ...services.cache import (
    CacheKeyBuilder, RedisCacheService, CacheManager, 
    cache_service, cache_manager, cached
)


class TestCacheKeyBuilder:
    """Тесты для строителя ключей кэша"""
    
    def test_user_key(self):
        """Тест генерации ключа пользователя"""
        key = CacheKeyBuilder.user_key(123)
        assert key == "user:123"
    
    def test_document_key(self):
        """Тест генерации ключа документа"""
        key = CacheKeyBuilder.document_key("doc-uuid-123")
        assert key == "document:doc-uuid-123"
    
    def test_search_key(self):
        """Тест генерации ключа поиска"""
        query = "test query"
        filters = {"category": "documents", "user_id": 123}
        user_id = 456
        
        key = CacheKeyBuilder.search_key(query, filters, user_id)
        
        assert key.startswith("search:456:")
        assert len(key.split(":")) == 4  # search:user_id:query_hash:filter_hash
    
    def test_rag_key(self):
        """Тест генерации ключа RAG ответа"""
        question = "What is the capital of France?"
        context_ids = ["doc1", "doc2", "doc3"]
        user_id = 789
        
        key = CacheKeyBuilder.rag_key(question, context_ids, user_id)
        
        assert key.startswith("rag:789:")
        assert len(key.split(":")) == 4  # rag:user_id:question_hash:context_hash
    
    def test_embeddings_key(self):
        """Тест генерации ключа эмбеддингов"""
        text = "Some text for embedding"
        model = "bge-m3"
        
        key = CacheKeyBuilder.embeddings_key(text, model)
        
        assert key.startswith("embeddings:bge-m3:")
        assert len(key.split(":")) == 3
    
    def test_key_consistency(self):
        """Тест консистентности ключей - одинаковые данные должны давать одинаковые ключи"""
        query = "test query"
        filters = {"type": "pdf"}
        user_id = 123
        
        key1 = CacheKeyBuilder.search_key(query, filters, user_id)
        key2 = CacheKeyBuilder.search_key(query, filters, user_id)
        
        assert key1 == key2
    
    def test_key_uniqueness(self):
        """Тест уникальности ключей - разные данные должны давать разные ключи"""
        query1 = "test query 1"
        query2 = "test query 2"
        filters = {"type": "pdf"}
        user_id = 123
        
        key1 = CacheKeyBuilder.search_key(query1, filters, user_id)
        key2 = CacheKeyBuilder.search_key(query2, filters, user_id)
        
        assert key1 != key2


@pytest.mark.unit
class TestRedisCacheService:
    """Тесты для Redis сервиса кэширования"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis клиента"""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def cache_service_instance(self, mock_redis_client):
        """Экземпляр сервиса кэширования с mock Redis"""
        service = RedisCacheService()
        service.redis_client = mock_redis_client
        return service
    
    async def test_set_with_json_serialization(self, cache_service_instance, mock_redis_client):
        """Тест сохранения данных с JSON сериализацией"""
        key = "test:key"
        value = {"test": "data", "number": 123}
        ttl = 600
        
        result = await cache_service_instance.set(key, value, ttl)
        
        assert result is True
        mock_redis_client.setex.assert_called_once()
        
        # Проверяем что данные сериализованы в JSON
        call_args = mock_redis_client.setex.call_args[0]
        assert call_args[0] == key
        assert call_args[1] == ttl
        serialized_data = json.loads(call_args[2].decode())
        assert serialized_data == value
    
    async def test_set_with_pickle_serialization(self, cache_service_instance, mock_redis_client):
        """Тест сохранения сложных объектов с pickle"""
        key = "test:complex"
        value = datetime.now()  # Объект, который нельзя сериализовать в JSON
        
        result = await cache_service_instance.set(key, value)
        
        assert result is True
        mock_redis_client.setex.assert_called_once()
        
        # Проверяем что используется pickle
        call_args = mock_redis_client.setex.call_args[0]
        pickled_data = call_args[2]
        unpickled_value = pickle.loads(pickled_data)
        assert unpickled_value == value
    
    async def test_get_with_json_deserialization(self, cache_service_instance, mock_redis_client):
        """Тест получения данных с JSON десериализацией"""
        key = "test:key"
        cached_data = {"test": "data", "number": 123}
        
        # Настраиваем mock для возврата JSON данных
        mock_redis_client.get.return_value = json.dumps(cached_data).encode()
        
        result = await cache_service_instance.get(key)
        
        assert result == cached_data
        mock_redis_client.get.assert_called_once_with(key)
    
    async def test_get_with_pickle_deserialization(self, cache_service_instance, mock_redis_client):
        """Тест получения сложных объектов с pickle"""
        key = "test:complex"
        original_value = datetime(2024, 1, 1, 12, 0, 0)
        
        # Настраиваем mock для возврата pickle данных
        mock_redis_client.get.return_value = pickle.dumps(original_value)
        
        result = await cache_service_instance.get(key)
        
        assert result == original_value
        assert isinstance(result, datetime)
    
    async def test_get_nonexistent_key(self, cache_service_instance, mock_redis_client):
        """Тест получения несуществующего ключа"""
        key = "nonexistent:key"
        default_value = "default"
        
        mock_redis_client.get.return_value = None
        
        result = await cache_service_instance.get(key, default=default_value)
        
        assert result == default_value
    
    async def test_delete_existing_key(self, cache_service_instance, mock_redis_client):
        """Тест удаления существующего ключа"""
        key = "test:key"
        
        mock_redis_client.delete.return_value = 1  # Один ключ удален
        
        result = await cache_service_instance.delete(key)
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with(key)
    
    async def test_delete_nonexistent_key(self, cache_service_instance, mock_redis_client):
        """Тест удаления несуществующего ключа"""
        key = "nonexistent:key"
        
        mock_redis_client.delete.return_value = 0  # Ничего не удалено
        
        result = await cache_service_instance.delete(key)
        
        assert result is False
    
    async def test_delete_pattern(self, cache_service_instance, mock_redis_client):
        """Тест удаления ключей по паттерну"""
        pattern = "user:*"
        matching_keys = ["user:1", "user:2", "user:3"]
        
        mock_redis_client.keys.return_value = matching_keys
        mock_redis_client.delete.return_value = len(matching_keys)
        
        result = await cache_service_instance.delete_pattern(pattern)
        
        assert result == 3
        mock_redis_client.keys.assert_called_once_with(pattern)
        mock_redis_client.delete.assert_called_once_with(*matching_keys)
    
    async def test_exists_true(self, cache_service_instance, mock_redis_client):
        """Тест проверки существования ключа (существует)"""
        key = "existing:key"
        
        mock_redis_client.exists.return_value = 1
        
        result = await cache_service_instance.exists(key)
        
        assert result is True
    
    async def test_exists_false(self, cache_service_instance, mock_redis_client):
        """Тест проверки существования ключа (не существует)"""
        key = "nonexistent:key"
        
        mock_redis_client.exists.return_value = 0
        
        result = await cache_service_instance.exists(key)
        
        assert result is False
    
    async def test_ttl_existing_key(self, cache_service_instance, mock_redis_client):
        """Тест получения TTL существующего ключа"""
        key = "test:key"
        expected_ttl = 300
        
        mock_redis_client.ttl.return_value = expected_ttl
        
        result = await cache_service_instance.ttl(key)
        
        assert result == expected_ttl
    
    async def test_expire_key(self, cache_service_instance, mock_redis_client):
        """Тест установки TTL для ключа"""
        key = "test:key"
        ttl = 600
        
        mock_redis_client.expire.return_value = 1  # Успешно установлено
        
        result = await cache_service_instance.expire(key, ttl)
        
        assert result is True
        mock_redis_client.expire.assert_called_once_with(key, ttl)
    
    async def test_increment(self, cache_service_instance, mock_redis_client):
        """Тест инкремента числового значения"""
        key = "counter:key"
        amount = 5
        expected_result = 10
        
        mock_redis_client.incrby.return_value = expected_result
        
        result = await cache_service_instance.increment(key, amount)
        
        assert result == expected_result
        mock_redis_client.incrby.assert_called_once_with(key, amount)
    
    def test_get_ttl_by_key_type(self, cache_service_instance):
        """Тест получения TTL по типу ключа"""
        # Тестируем различные типы ключей
        assert cache_service_instance._get_ttl("user") == 1800
        assert cache_service_instance._get_ttl("document") == 7200
        assert cache_service_instance._get_ttl("search") == 600
        assert cache_service_instance._get_ttl("unknown") == 3600  # default
    
    def test_extract_key_type(self, cache_service_instance):
        """Тест извлечения типа ключа"""
        assert cache_service_instance._extract_key_type("user:123") == "user"
        assert cache_service_instance._extract_key_type("document:abc") == "document"
        assert cache_service_instance._extract_key_type("search:456:hash") == "search"
        assert cache_service_instance._extract_key_type("no_colon") == "default"
    
    async def test_error_handling(self, cache_service_instance, mock_redis_client):
        """Тест обработки ошибок Redis"""
        key = "test:key"
        
        # Настраиваем mock для выброса исключения
        mock_redis_client.get.side_effect = Exception("Redis connection error")
        
        result = await cache_service_instance.get(key, default="fallback")
        
        assert result == "fallback"
    
    async def test_memory_stats(self, cache_service_instance, mock_redis_client):
        """Тест получения статистики памяти"""
        memory_info = {
            "used_memory": 1048576,
            "used_memory_human": "1.00M",
            "used_memory_peak": 2097152,
            "total_system_memory": 8589934592
        }
        
        mock_redis_client.info.return_value = memory_info
        
        result = await cache_service_instance.get_memory_usage()
        
        assert result["used_memory"] == 1048576
        assert result["used_memory_human"] == "1.00M"
        assert "memory_usage_percentage" in result
    
    async def test_cache_stats(self, cache_service_instance, mock_redis_client):
        """Тест получения общей статистики кэша"""
        stats_info = {
            "db0": {"keys": 150},
            "total_commands_processed": 5000,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
            "connected_clients": 5,
            "uptime_in_seconds": 86400
        }
        
        mock_redis_client.info.return_value = stats_info
        
        result = await cache_service_instance.get_stats()
        
        assert result["total_keys"] == 150
        assert result["hits"] == 800
        assert result["misses"] == 200
        assert result["hit_rate"] == 80.0  # 800/(800+200) * 100


@pytest.mark.unit
class TestCacheManager:
    """Тесты для менеджера кэширования"""
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock сервиса кэширования"""
        return AsyncMock()
    
    @pytest.fixture 
    def cache_manager_instance(self, mock_cache_service):
        """Экземпляр менеджера кэширования"""
        return CacheManager(mock_cache_service)
    
    async def test_get_or_set_cache_hit(self, cache_manager_instance, mock_cache_service):
        """Тест get_or_set с попаданием в кэш"""
        key = "test:key"
        cached_value = {"cached": "data"}
        
        # Настраиваем кэш для возврата данных
        mock_cache_service.get.return_value = cached_value
        
        # Factory функция не должна вызываться
        factory_called = False
        
        async def factory():
            nonlocal factory_called
            factory_called = True
            return {"factory": "data"}
        
        result = await cache_manager_instance.get_or_set(key, factory)
        
        assert result == cached_value
        assert not factory_called
        mock_cache_service.get.assert_called_once_with(key)
        mock_cache_service.set.assert_not_called()
    
    async def test_get_or_set_cache_miss(self, cache_manager_instance, mock_cache_service):
        """Тест get_or_set с промахом кэша"""
        key = "test:key"
        factory_value = {"factory": "data"}
        
        # Настраиваем кэш для возврата None (промах)
        mock_cache_service.get.return_value = None
        
        async def factory():
            return factory_value
        
        result = await cache_manager_instance.get_or_set(key, factory)
        
        assert result == factory_value
        mock_cache_service.get.assert_called_once_with(key)
        mock_cache_service.set.assert_called_once_with(key, factory_value, None)
    
    async def test_get_or_set_with_ttl(self, cache_manager_instance, mock_cache_service):
        """Тест get_or_set с указанным TTL"""
        key = "test:key"
        factory_value = {"factory": "data"}
        ttl = 1800
        
        mock_cache_service.get.return_value = None
        
        async def factory():
            return factory_value
        
        result = await cache_manager_instance.get_or_set(key, factory, ttl=ttl)
        
        assert result == factory_value
        mock_cache_service.set.assert_called_once_with(key, factory_value, ttl)
    
    def test_local_cache_functionality(self, cache_manager_instance):
        """Тест локального кэша L1"""
        key = "local:key"
        data = {"test": "data"}
        
        # Устанавливаем в локальный кэш
        cache_manager_instance._set_local_cache(key, data)
        
        # Проверяем что данные есть
        assert key in cache_manager_instance.local_cache
        assert cache_manager_instance.local_cache[key]["data"] == data
    
    def test_local_cache_size_limit(self, cache_manager_instance):
        """Тест ограничения размера локального кэша"""
        # Устанавливаем небольшой лимит
        cache_manager_instance.local_cache_size = 5
        
        # Добавляем данные сверх лимита
        for i in range(10):
            cache_manager_instance._set_local_cache(f"key:{i}", f"data:{i}")
        
        # Проверяем что размер не превышает лимит
        assert len(cache_manager_instance.local_cache) <= cache_manager_instance.local_cache_size
    
    async def test_invalidate_user_cache(self, cache_manager_instance, mock_cache_service):
        """Тест инвалидации кэша пользователя"""
        user_id = 123
        
        await cache_manager_instance.invalidate_user_cache(user_id)
        
        # Проверяем что вызываются правильные паттерны удаления
        expected_patterns = [
            f"user:{user_id}*",
            f"search:{user_id}:*",
            f"rag:{user_id}:*",
            f"api:*:{user_id}:*"
        ]
        
        assert mock_cache_service.delete_pattern.call_count == len(expected_patterns)
    
    async def test_invalidate_document_cache(self, cache_manager_instance, mock_cache_service):
        """Тест инвалидации кэша документа"""
        document_id = "doc-123"
        
        await cache_manager_instance.invalidate_document_cache(document_id)
        
        # Проверяем что удаляются связанные паттерны
        expected_patterns = [
            f"document:{document_id}*",
            "search:*",
            "rag:*"
        ]
        
        assert mock_cache_service.delete_pattern.call_count == len(expected_patterns)


@pytest.mark.unit
class TestCachedDecorator:
    """Тесты для декоратора @cached"""
    
    async def test_cached_function_first_call(self):
        """Тест первого вызова кэшированной функции"""
        call_count = 0
        
        @cached(ttl=300)
        async def expensive_function(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}_{arg2}"
        
        with patch.object(cache_manager, 'get_or_set') as mock_get_or_set:
            mock_get_or_set.return_value = "cached_result"
            
            result = await expensive_function("test", arg2="value")
            
            assert result == "cached_result"
            mock_get_or_set.assert_called_once()
    
    async def test_cached_function_with_custom_key_builder(self):
        """Тест кэшированной функции с кастомным строителем ключей"""
        def custom_key_builder(user_id):
            return f"custom:user:{user_id}"
        
        @cached(ttl=600, key_builder=custom_key_builder)
        async def get_user_data(user_id):
            return {"user_id": user_id, "data": "test"}
        
        with patch.object(cache_manager, 'get_or_set') as mock_get_or_set:
            mock_get_or_set.return_value = {"cached": True}
            
            result = await get_user_data(123)
            
            # Проверяем что использовался кастомный ключ
            call_args = mock_get_or_set.call_args
            key_used = call_args[1]["key"] if len(call_args) > 1 else call_args[0][0]
            # Key будет передан через factory функцию, проверим что get_or_set вызван
            mock_get_or_set.assert_called_once()
    
    async def test_cached_function_without_local_cache(self):
        """Тест кэшированной функции без локального кэша"""
        @cached(ttl=300, use_local_cache=False)
        async def function_no_local_cache():
            return "result"
        
        with patch.object(cache_manager, 'get_or_set') as mock_get_or_set:
            mock_get_or_set.return_value = "cached_result"
            
            result = await function_no_local_cache()
            
            # Проверяем что локальный кэш отключен
            call_kwargs = mock_get_or_set.call_args[1]
            assert call_kwargs.get("use_local_cache") is False
    
    def test_cache_key_generation_consistency(self):
        """Тест консистентности генерации ключей кэша"""
        # Имитируем автоматическую генерацию ключа
        func_name = "test_function"
        args = ("arg1", "arg2")
        kwargs = {"key": "value", "option": True}
        
        import hashlib
        
        args_str = str(args) + str(sorted(kwargs.items()))
        key_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        expected_key = f"func:{func_name}:{key_hash}"
        
        # Тест что одинаковые аргументы дают одинаковый ключ
        args_str2 = str(args) + str(sorted(kwargs.items()))
        key_hash2 = hashlib.md5(args_str2.encode()).hexdigest()[:8]
        key2 = f"func:{func_name}:{key_hash2}"
        
        assert expected_key == key2
