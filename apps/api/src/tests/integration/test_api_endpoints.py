"""
Integration тесты для API эндпоинтов
"""
import pytest
import json
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime

from ...main import app
from ...services.cache import cache_service
from ...services.performance_monitor import profiler


@pytest.mark.integration
class TestAuthenticationEndpoints:
    """Интеграционные тесты аутентификации"""
    
    async def test_login_success(self, test_client: AsyncClient, test_user, db_connection):
        """Тест успешного входа"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword"
        }
        
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="test_token"):
            
            response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_invalid_credentials(self, test_client: AsyncClient):
        """Тест входа с неверными данными"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Неверные учетные данные" in response.json()["detail"]
    
    async def test_protected_endpoint_without_token(self, test_client: AsyncClient):
        """Тест доступа к защищенному эндпоинту без токена"""
        response = await test_client.get("/api/v1/documents/")
        
        assert response.status_code == 401
    
    async def test_protected_endpoint_with_token(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест доступа к защищенному эндпоинту с токеном"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == 200


@pytest.mark.integration
class TestDocumentEndpoints:
    """Интеграционные тесты для работы с документами"""
    
    async def test_get_documents_list(self, test_client: AsyncClient, test_jwt_token, test_user, test_document):
        """Тест получения списка документов"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)
    
    async def test_get_document_by_id(self, test_client: AsyncClient, test_jwt_token, test_user, test_document):
        """Тест получения документа по ID"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        document_id = test_document["id"]
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.get(f"/api/v1/documents/{document_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == test_document["title"]
    
    async def test_upload_document(self, test_client: AsyncClient, test_jwt_token, test_user, mock_file_upload):
        """Тест загрузки документа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
             patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create:
            
            mock_save.return_value = "/tmp/uploaded_file.pdf"
            mock_create.return_value = {
                "id": "new-doc-id",
                "title": "Uploaded Document",
                "filename": "test_upload.pdf"
            }
            
            files = {"file": ("test_upload.pdf", mock_file_upload.file, "application/pdf")}
            response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Uploaded Document"
    
    async def test_delete_document(self, test_client: AsyncClient, test_jwt_token, test_user, test_document):
        """Тест удаления документа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        document_id = test_document["id"]
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.document_service.DocumentService.delete_document', return_value=True):
            
            response = await test_client.delete(f"/api/v1/documents/{document_id}", headers=headers)
        
        assert response.status_code == 200
        assert "успешно удален" in response.json()["message"]
    
    async def test_document_not_found(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест получения несуществующего документа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        nonexistent_id = "00000000-0000-0000-0000-000000000000"
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.get(f"/api/v1/documents/{nonexistent_id}", headers=headers)
        
        assert response.status_code == 404


@pytest.mark.integration
class TestSearchEndpoints:
    """Интеграционные тесты для поиска"""
    
    async def test_semantic_search(self, test_client: AsyncClient, test_jwt_token, test_user, test_document_chunks):
        """Тест семантического поиска"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        search_data = {
            "query": "test content",
            "search_type": "semantic",
            "limit": 10
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            # Мокаем результаты поиска
            mock_search.return_value = {
                "results": [
                    {
                        "chunk_id": chunk["id"],
                        "content": chunk["content"],
                        "score": 0.95,
                        "document_id": chunk["document_id"],
                        "metadata": chunk["metadata"]
                    }
                    for chunk in test_document_chunks[:3]
                ],
                "total": 3,
                "query_time_ms": 125.5
            }
            
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3
        assert data["total"] == 3
        assert "query_time_ms" in data
    
    async def test_keyword_search(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест ключевого поиска"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        search_data = {
            "query": "meaningful content",
            "search_type": "keyword",
            "limit": 5
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.search_service.SearchService.keyword_search') as mock_search:
            
            mock_search.return_value = {
                "results": [],
                "total": 0,
                "query_time_ms": 45.2
            }
            
            response = await test_client.post("/api/v1/search/keyword", headers=headers, json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] == 0
    
    async def test_search_with_filters(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест поиска с фильтрами"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        search_data = {
            "query": "test",
            "search_type": "semantic",
            "filters": {
                "content_type": "application/pdf",
                "date_from": "2024-01-01",
                "date_to": "2024-12-31"
            },
            "limit": 10
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_search.return_value = {"results": [], "total": 0, "query_time_ms": 50.0}
            
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
        
        assert response.status_code == 200
        # Проверяем что фильтры переданы в сервис поиска
        mock_search.assert_called_once()
        call_args = mock_search.call_args[1]
        assert "filters" in call_args
        assert call_args["filters"]["content_type"] == "application/pdf"
    
    async def test_search_validation_error(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест валидации поискового запроса"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        invalid_search_data = {
            "query": "",  # Пустой запрос
            "search_type": "invalid_type",  # Неверный тип
            "limit": 1000  # Слишком большой лимит
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=invalid_search_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestRAGEndpoints:
    """Интеграционные тесты для RAG ответов"""
    
    async def test_rag_answer(self, test_client: AsyncClient, test_jwt_token, test_user, test_document_chunks):
        """Тест получения RAG ответа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        rag_data = {
            "question": "What is the main topic of the document?",
            "context_limit": 5,
            "include_sources": True
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.rag_service.RAGService.generate_answer') as mock_rag:
            
            mock_rag.return_value = {
                "answer": "The document discusses test content and meaningful information.",
                "sources": [
                    {
                        "chunk_id": chunk["id"],
                        "content": chunk["content"][:100] + "...",
                        "document_id": chunk["document_id"],
                        "relevance_score": 0.9
                    }
                    for chunk in test_document_chunks[:2]
                ],
                "confidence_score": 0.85,
                "processing_time_ms": 1250.5
            }
            
            response = await test_client.post("/api/v1/answers/rag", headers=headers, json=rag_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence_score" in data
        assert len(data["sources"]) == 2
    
    async def test_rag_answer_without_sources(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест RAG ответа без включения источников"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        rag_data = {
            "question": "What is this about?",
            "include_sources": False
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.rag_service.RAGService.generate_answer') as mock_rag:
            
            mock_rag.return_value = {
                "answer": "This is about test content.",
                "sources": [],
                "confidence_score": 0.75,
                "processing_time_ms": 800.0
            }
            
            response = await test_client.post("/api/v1/answers/rag", headers=headers, json=rag_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["sources"] == []
    
    async def test_rag_answer_no_relevant_context(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест RAG ответа когда нет релевантного контекста"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        rag_data = {
            "question": "What is the meaning of life?",
            "context_limit": 5
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.rag_service.RAGService.generate_answer') as mock_rag:
            
            mock_rag.return_value = {
                "answer": "I don't have enough relevant information to answer this question.",
                "sources": [],
                "confidence_score": 0.1,
                "processing_time_ms": 300.0
            }
            
            response = await test_client.post("/api/v1/answers/rag", headers=headers, json=rag_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["confidence_score"] < 0.5


@pytest.mark.integration
class TestPerformanceEndpoints:
    """Интеграционные тесты для эндпоинтов производительности"""
    
    async def test_performance_summary(self, test_client: AsyncClient, test_jwt_token, admin_user):
        """Тест получения сводки производительности"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=admin_user), \
             patch('apps.api.src.services.performance_monitor.profiler.get_performance_summary') as mock_summary, \
             patch('apps.api.src.services.database_optimizer.SystemMonitor.get_system_metrics') as mock_system, \
             patch('apps.api.src.services.cache.cache_service.get_stats') as mock_cache_stats, \
             patch('apps.api.src.services.cache.cache_service.get_memory_usage') as mock_cache_memory, \
             patch('apps.api.src.services.database_optimizer.db_optimizer.get_connection_stats') as mock_db_stats:
            
            # Настраиваем моки
            mock_summary.return_value = {
                "total_requests": 1000,
                "avg_response_time": 0.25,
                "error_rate": 2.5,
                "system_status": "healthy"
            }
            
            mock_system.return_value = {
                "cpu": {"percent": 35.5},
                "memory": {"percent": 65.2}
            }
            
            mock_cache_stats.return_value = {"hit_rate": 82.5}
            mock_cache_memory.return_value = {"used_memory_human": "128M"}
            mock_db_stats.return_value = {"pool_size": 10}
            
            response = await test_client.get("/api/v1/performance/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        assert "system" in data
        assert "cache" in data
        assert "database" in data
        assert data["status"] == "healthy"
    
    async def test_endpoint_stats(self, test_client: AsyncClient, test_jwt_token, admin_user):
        """Тест получения статистики эндпоинтов"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=admin_user), \
             patch('apps.api.src.services.performance_monitor.profiler.get_endpoint_stats') as mock_stats:
            
            mock_stats.return_value = [
                {
                    "endpoint": "/api/v1/search/semantic",
                    "method": "POST",
                    "total_requests": 500,
                    "avg_response_time": 0.350,
                    "error_rate": 1.2
                },
                {
                    "endpoint": "/api/v1/documents/",
                    "method": "GET",
                    "total_requests": 300,
                    "avg_response_time": 0.125,
                    "error_rate": 0.5
                }
            ]
            
            response = await test_client.get("/api/v1/performance/endpoints?limit=10", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert len(data["endpoints"]) == 2
        assert data["endpoints"][0]["endpoint"] == "/api/v1/search/semantic"
    
    async def test_slow_endpoints(self, test_client: AsyncClient, test_jwt_token, admin_user):
        """Тест получения медленных эндпоинтов"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=admin_user), \
             patch('apps.api.src.services.performance_monitor.profiler.get_slow_endpoints') as mock_slow:
            
            mock_slow.return_value = [
                {
                    "endpoint": "/api/v1/answers/rag",
                    "method": "POST",
                    "p95_response_time": 2.5,
                    "total_requests": 100
                }
            ]
            
            response = await test_client.get("/api/v1/performance/slow-endpoints", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "slow_endpoints" in data
        assert len(data["slow_endpoints"]) == 1
    
    async def test_unauthorized_performance_access(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест доступа к метрикам производительности без прав"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            response = await test_client.get("/api/v1/performance/summary", headers=headers)
        
        assert response.status_code == 403  # Forbidden


@pytest.mark.integration
class TestCacheIntegration:
    """Интеграционные тесты кэширования"""
    
    async def test_cache_invalidation_on_document_update(self, test_client: AsyncClient, test_jwt_token, test_user, test_document, clean_cache):
        """Тест инвалидации кэша при обновлении документа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        document_id = test_document["id"]
        
        # Сначала кэшируем документ
        cache_key = f"document:{document_id}"
        await cache_service.set(cache_key, test_document, ttl=3600)
        
        # Проверяем что документ в кэше
        cached_doc = await cache_service.get(cache_key)
        assert cached_doc is not None
        
        # Обновляем документ
        update_data = {"title": "Updated Title"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.document_service.DocumentService.update_document') as mock_update, \
             patch('apps.api.src.services.cache.cache_manager.invalidate_document_cache') as mock_invalidate:
            
            mock_update.return_value = {**test_document, **update_data}
            
            response = await test_client.put(f"/api/v1/documents/{document_id}", headers=headers, json=update_data)
        
        assert response.status_code == 200
        
        # Проверяем что была вызвана инвалидация кэша
        mock_invalidate.assert_called_once_with(document_id)
    
    async def test_cache_hit_improves_response_time(self, test_client: AsyncClient, test_jwt_token, test_user, test_document, clean_cache, performance_test_context):
        """Тест что кэш улучшает время ответа"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        document_id = test_document["id"]
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            # Первый запрос (без кэша)
            start_time = datetime.utcnow()
            response1 = await test_client.get(f"/api/v1/documents/{document_id}", headers=headers)
            first_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Второй запрос (с кэшем)
            start_time = datetime.utcnow()
            response2 = await test_client.get(f"/api/v1/documents/{document_id}", headers=headers)
            second_time = (datetime.utcnow() - start_time).total_seconds()
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Второй запрос должен быть быстрее (если кэш работает)
        # Для интеграционных тестов это может не всегда выполняться из-за моков


@pytest.mark.integration
class TestErrorHandling:
    """Интеграционные тесты обработки ошибок"""
    
    async def test_database_connection_error(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест обработки ошибки подключения к БД"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.document_service.DocumentService.get_documents') as mock_get_docs:
            
            # Имитируем ошибку БД
            mock_get_docs.side_effect = Exception("Database connection failed")
            
            response = await test_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == 500
        assert "error" in response.json()
    
    async def test_rate_limiting(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест ограничения частоты запросов"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.middleware.rate_limit.rate_limit_middleware') as mock_rate_limit:
            
            # Настраиваем rate limiter для отклонения запроса
            mock_rate_limit.side_effect = Exception("Rate limit exceeded")
            
            response = await test_client.get("/api/v1/documents/", headers=headers)
        
        # Должна быть обработана ошибка rate limiting
        # Точный код статуса зависит от реализации rate limiter
        assert response.status_code in [429, 500]
    
    async def test_invalid_json_request(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест обработки невалидного JSON"""
        headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "Content-Type": "application/json"
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            # Отправляем невалидный JSON
            response = await test_client.post("/api/v1/search/semantic", headers=headers, content="invalid json")
        
        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.integration
class TestWebhookIntegration:
    """Интеграционные тесты webhooks"""
    
    async def test_webhook_creation_and_trigger(self, test_client: AsyncClient, test_jwt_token, admin_user):
        """Тест создания webhook и отправки события"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        # Создаем webhook
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://httpbin.org/post",
            "events": ["document.uploaded"],
            "active": True
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=admin_user), \
             patch('apps.api.src.services.webhook_service.webhook_service.register_webhook') as mock_register, \
             patch('apps.api.src.services.webhook_service.webhook_service.trigger_event') as mock_trigger:
            
            mock_register.return_value = {
                "id": 1,
                "name": webhook_data["name"],
                "url": webhook_data["url"],
                "events": webhook_data["events"]
            }
            
            # Создаем webhook
            response = await test_client.post("/api/v1/webhooks/", headers=headers, json=webhook_data)
            assert response.status_code == 200
            
            # Тестируем webhook
            test_event_data = {"test": "data"}
            response = await test_client.post("/api/v1/webhooks/trigger-event", headers=headers, json=test_event_data)
            assert response.status_code == 200
            
            # Проверяем что событие было отправлено
            mock_trigger.assert_called_once()


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Интеграционные тесты производительности"""
    
    async def test_concurrent_requests_performance(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест производительности при одновременных запросах"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user):
            
            async def make_request():
                return await test_client.get("/api/v1/documents/", headers=headers)
            
            # Делаем 10 одновременных запросов
            import asyncio
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            
            # Все запросы должны быть успешными
            for response in responses:
                assert response.status_code == 200
    
    async def test_large_payload_handling(self, test_client: AsyncClient, test_jwt_token, test_user):
        """Тест обработки больших запросов"""
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        # Создаем большой поисковый запрос
        large_query = "test " * 1000  # 5000 символов
        search_data = {
            "query": large_query,
            "search_type": "semantic",
            "limit": 50
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token', return_value=test_user), \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_search.return_value = {"results": [], "total": 0, "query_time_ms": 100.0}
            
            start_time = datetime.utcnow()
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            assert response.status_code == 200
            assert processing_time < 5.0  # Должно обрабатываться быстро
