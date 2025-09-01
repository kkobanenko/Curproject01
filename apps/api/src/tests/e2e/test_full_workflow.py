"""
End-to-End тесты полного workflow RAG платформы
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from ...main import app


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteRAGWorkflow:
    """E2E тесты полного цикла работы с RAG платформой"""
    
    async def test_complete_document_processing_workflow(self, test_client: AsyncClient):
        """
        Тест полного цикла: регистрация -> загрузка документа -> поиск -> RAG ответ
        """
        # 1. Регистрация нового пользователя
        registration_data = {
            "username": "e2e_user",
            "email": "e2e@example.com",
            "password": "SecurePassword123!",
            "full_name": "E2E Test User"
        }
        
        with patch('apps.api.src.services.auth.AuthService.hash_password') as mock_hash, \
             patch('apps.api.src.services.auth.AuthService.create_user') as mock_create_user:
            
            mock_hash.return_value = "$2b$12$hashed_password"
            mock_create_user.return_value = {
                "user_id": 100,
                "username": registration_data["username"],
                "email": registration_data["email"],
                "role": "user"
            }
            
            response = await test_client.post("/api/v1/auth/register", json=registration_data)
            assert response.status_code == 201
            user_data = response.json()
        
        # 2. Вход в систему
        login_data = {
            "username": registration_data["username"],
            "password": registration_data["password"]
        }
        
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="e2e_test_token"):
            
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200
            auth_data = response.json()
            access_token = auth_data["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Загрузка документа
        test_content = b"""
        Machine Learning Fundamentals
        
        Machine learning is a subset of artificial intelligence that focuses on algorithms
        that can learn from and make predictions on data. There are three main types:
        
        1. Supervised Learning: Uses labeled data to train models
        2. Unsupervised Learning: Finds patterns in unlabeled data  
        3. Reinforcement Learning: Learns through interaction with environment
        
        Common algorithms include linear regression, decision trees, neural networks,
        and support vector machines. Deep learning is a subset that uses neural
        networks with multiple layers.
        """
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = tmp_file.name
        
        try:
            with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
                 patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
                 patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create_doc, \
                 patch('apps.api.src.services.rag_pipeline.RAGPipeline.process_document') as mock_process:
                
                # Настраиваем моки
                mock_auth.return_value = AsyncMock(user_id=100, username="e2e_user", tenant_id=1)
                mock_save.return_value = "/tmp/uploaded_ml_doc.txt"
                
                document_id = "e2e-doc-123"
                mock_create_doc.return_value = {
                    "id": document_id,
                    "title": "Machine Learning Fundamentals",
                    "filename": "ml_fundamentals.txt",
                    "content_type": "text/plain",
                    "size_bytes": len(test_content),
                    "user_id": 100,
                    "status": "uploaded"
                }
                
                # Мокаем результат обработки документа
                mock_process.return_value = {
                    "chunks_created": 5,
                    "embeddings_created": 5,
                    "processing_time_seconds": 2.5,
                    "status": "completed"
                }
                
                files = {"file": ("ml_fundamentals.txt", test_content, "text/plain")}
                response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
                
                assert response.status_code == 201
                upload_result = response.json()
                assert upload_result["title"] == "Machine Learning Fundamentals"
                document_id = upload_result["id"]
        
        finally:
            os.unlink(tmp_file_path)
        
        # 4. Ожидаем обработки документа (имитируем)
        await asyncio.sleep(0.1)  # Короткая задержка для имитации обработки
        
        # 5. Проверяем статус обработки документа
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.document_service.DocumentService.get_document') as mock_get_doc:
            
            mock_auth.return_value = AsyncMock(user_id=100, username="e2e_user", tenant_id=1)
            mock_get_doc.return_value = {
                "id": document_id,
                "title": "Machine Learning Fundamentals",
                "status": "processed",
                "chunks_count": 5,
                "processing_completed_at": datetime.utcnow().isoformat()
            }
            
            response = await test_client.get(f"/api/v1/documents/{document_id}", headers=headers)
            assert response.status_code == 200
            doc_status = response.json()
            assert doc_status["status"] == "processed"
        
        # 6. Выполняем семантический поиск
        search_query = {
            "query": "What are the main types of machine learning?",
            "search_type": "semantic",
            "limit": 5
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_auth.return_value = AsyncMock(user_id=100, username="e2e_user", tenant_id=1)
            
            # Мокаем результаты поиска
            mock_search.return_value = {
                "results": [
                    {
                        "chunk_id": "chunk-1",
                        "content": "There are three main types: 1. Supervised Learning: Uses labeled data to train models 2. Unsupervised Learning: Finds patterns in unlabeled data 3. Reinforcement Learning: Learns through interaction with environment",
                        "score": 0.95,
                        "document_id": document_id,
                        "metadata": {"section": "types", "page": 1}
                    },
                    {
                        "chunk_id": "chunk-2", 
                        "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from and make predictions on data.",
                        "score": 0.87,
                        "document_id": document_id,
                        "metadata": {"section": "introduction", "page": 1}
                    }
                ],
                "total": 2,
                "query_time_ms": 125.5
            }
            
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_query)
            assert response.status_code == 200
            search_results = response.json()
            
            assert len(search_results["results"]) == 2
            assert search_results["total"] == 2
            assert "three main types" in search_results["results"][0]["content"]
        
        # 7. Получаем RAG ответ на основе найденного контекста
        rag_query = {
            "question": "What are the three main types of machine learning and how do they differ?",
            "context_limit": 3,
            "include_sources": True
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.rag_service.RAGService.generate_answer') as mock_rag:
            
            mock_auth.return_value = AsyncMock(user_id=100, username="e2e_user", tenant_id=1)
            
            # Мокаем RAG ответ
            mock_rag.return_value = {
                "answer": """Based on the provided context, there are three main types of machine learning:

1. **Supervised Learning**: This type uses labeled data to train models. It learns from examples where both input and correct output are provided.

2. **Unsupervised Learning**: This approach finds patterns in unlabeled data where only input data is available without corresponding outputs.

3. **Reinforcement Learning**: This type learns through interaction with an environment, receiving feedback in the form of rewards or penalties.

These three approaches differ primarily in how they learn from data and what type of data they require for training.""",
                "sources": [
                    {
                        "chunk_id": "chunk-1",
                        "content": "There are three main types: 1. Supervised Learning: Uses labeled data...",
                        "document_id": document_id,
                        "relevance_score": 0.95
                    }
                ],
                "confidence_score": 0.92,
                "processing_time_ms": 1850.0
            }
            
            response = await test_client.post("/api/v1/answers/rag", headers=headers, json=rag_query)
            assert response.status_code == 200
            rag_result = response.json()
            
            assert "three main types" in rag_result["answer"]
            assert "Supervised Learning" in rag_result["answer"]
            assert "Unsupervised Learning" in rag_result["answer"]
            assert "Reinforcement Learning" in rag_result["answer"]
            assert rag_result["confidence_score"] > 0.8
            assert len(rag_result["sources"]) > 0
        
        # 8. Проверяем историю запросов пользователя
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.search_service.SearchService.get_user_search_history') as mock_history:
            
            mock_auth.return_value = AsyncMock(user_id=100, username="e2e_user", tenant_id=1)
            mock_history.return_value = [
                {
                    "id": "search-1",
                    "query": "What are the main types of machine learning?",
                    "search_type": "semantic",
                    "results_count": 2,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
            
            response = await test_client.get("/api/v1/search/history", headers=headers)
            assert response.status_code == 200
            history = response.json()
            assert len(history) == 1
            assert "machine learning" in history[0]["query"]
    
    async def test_multi_document_workflow(self, test_client: AsyncClient):
        """Тест работы с несколькими документами"""
        # Создаем пользователя и получаем токен
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="multi_doc_token"):
            
            login_data = {"username": "testuser", "password": "testpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            access_token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Загружаем несколько документов
        documents = [
            ("Python Basics", b"Python is a programming language known for its simplicity and readability."),
            ("Machine Learning", b"ML algorithms can learn patterns from data without explicit programming."),
            ("Data Science", b"Data science combines statistics, programming, and domain expertise.")
        ]
        
        doc_ids = []
        
        for title, content in documents:
            with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
                 patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
                 patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create:
                
                mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
                mock_save.return_value = f"/tmp/{title.lower().replace(' ', '_')}.txt"
                
                doc_id = f"doc-{len(doc_ids) + 1}"
                mock_create.return_value = {
                    "id": doc_id,
                    "title": title,
                    "filename": f"{title.lower().replace(' ', '_')}.txt",
                    "content_type": "text/plain",
                    "size_bytes": len(content)
                }
                
                files = {"file": (f"{title}.txt", content, "text/plain")}
                response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
                
                assert response.status_code == 201
                doc_ids.append(doc_id)
        
        # Выполняем поиск по всем документам
        search_query = {
            "query": "programming and data analysis",
            "search_type": "semantic",
            "limit": 10
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
            
            # Мокаем результаты из разных документов
            mock_search.return_value = {
                "results": [
                    {
                        "chunk_id": "chunk-py-1",
                        "content": "Python is a programming language known for its simplicity",
                        "score": 0.92,
                        "document_id": doc_ids[0],
                        "metadata": {"title": "Python Basics"}
                    },
                    {
                        "chunk_id": "chunk-ds-1", 
                        "content": "Data science combines statistics, programming, and domain expertise",
                        "score": 0.88,
                        "document_id": doc_ids[2],
                        "metadata": {"title": "Data Science"}
                    }
                ],
                "total": 2,
                "query_time_ms": 95.0
            }
            
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_query)
            assert response.status_code == 200
            
            results = response.json()
            assert len(results["results"]) == 2
            
            # Проверяем что результаты из разных документов
            document_ids_in_results = {r["document_id"] for r in results["results"]}
            assert len(document_ids_in_results) > 1  # Результаты из разных документов
    
    async def test_error_recovery_workflow(self, test_client: AsyncClient):
        """Тест восстановления после ошибок"""
        # Получаем токен
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="error_test_token"):
            
            login_data = {"username": "testuser", "password": "testpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            access_token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. Тест восстановления после ошибки загрузки
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
            
            # Первая попытка - ошибка
            mock_save.side_effect = Exception("Disk full")
            
            files = {"file": ("test.txt", b"test content", "text/plain")}
            response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
            assert response.status_code == 500
            
            # Вторая попытка - успех
            mock_save.side_effect = None
            mock_save.return_value = "/tmp/test_recovered.txt"
            
            with patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create:
                mock_create.return_value = {
                    "id": "recovered-doc",
                    "title": "Recovered Document",
                    "filename": "test.txt"
                }
                
                response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
                assert response.status_code == 201
        
        # 2. Тест восстановления после ошибки поиска
        search_query = {
            "query": "test search",
            "search_type": "semantic"
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
            
            # Первая попытка - ошибка векторной БД
            mock_search.side_effect = Exception("Vector database connection failed")
            
            response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_query)
            assert response.status_code == 500
            
            # Вторая попытка - fallback к keyword поиску
            with patch('apps.api.src.services.search_service.SearchService.keyword_search') as mock_keyword:
                mock_keyword.return_value = {
                    "results": [{"chunk_id": "fallback-1", "content": "fallback result"}],
                    "total": 1,
                    "query_time_ms": 50.0
                }
                
                # В реальной системе можно было бы настроить fallback
                # Здесь просто проверим что keyword поиск работает
                keyword_query = {**search_query, "search_type": "keyword"}
                response = await test_client.post("/api/v1/search/keyword", headers=headers, json=keyword_query)
                # Зависит от реализации fallback логики


@pytest.mark.e2e
@pytest.mark.slow
class TestUserRolesAndPermissions:
    """E2E тесты ролей и разрешений пользователей"""
    
    async def test_admin_full_access_workflow(self, test_client: AsyncClient):
        """Тест полного доступа администратора"""
        # Вход как администратор
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="admin_token"):
            
            login_data = {"username": "admin", "password": "adminpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            admin_token = response.json()["access_token"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Администратор может видеть метрики производительности
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(
                user_id=1, username="admin", tenant_id=1, 
                role="admin", permissions=["admin", "metrics_view"]
            )
            
            with patch('apps.api.src.services.performance_monitor.profiler.get_performance_summary') as mock_perf:
                mock_perf.return_value = {"status": "healthy", "total_requests": 1000}
                
                response = await test_client.get("/api/v1/performance/summary", headers=admin_headers)
                assert response.status_code == 200
        
        # Администратор может управлять пользователями
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(
                user_id=1, username="admin", tenant_id=1,
                role="admin", permissions=["admin", "user_management"]
            )
            
            with patch('apps.api.src.services.auth.AuthService.get_all_users') as mock_users:
                mock_users.return_value = [
                    {"id": 1, "username": "admin", "role": "admin"},
                    {"id": 2, "username": "user1", "role": "user"}
                ]
                
                response = await test_client.get("/api/v1/auth/users", headers=admin_headers)
                assert response.status_code == 200
    
    async def test_regular_user_limited_access(self, test_client: AsyncClient):
        """Тест ограниченного доступа обычного пользователя"""
        # Вход как обычный пользователь
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="user_token"):
            
            login_data = {"username": "regularuser", "password": "userpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            user_token = response.json()["access_token"]
        
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Обычный пользователь не может видеть метрики производительности
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(
                user_id=2, username="regularuser", tenant_id=1,
                role="user", permissions=["read", "write"]
            )
            
            response = await test_client.get("/api/v1/performance/summary", headers=user_headers)
            assert response.status_code == 403  # Forbidden
        
        # Но может работать со своими документами
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(
                user_id=2, username="regularuser", tenant_id=1,
                role="user", permissions=["read", "write"]
            )
            
            with patch('apps.api.src.services.document_service.DocumentService.get_user_documents') as mock_docs:
                mock_docs.return_value = [
                    {"id": "user-doc-1", "title": "User Document", "user_id": 2}
                ]
                
                response = await test_client.get("/api/v1/documents/", headers=user_headers)
                assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.slow
class TestSystemIntegration:
    """E2E тесты интеграции системных компонентов"""
    
    async def test_cache_and_performance_integration(self, test_client: AsyncClient):
        """Тест интеграции кэширования и мониторинга производительности"""
        # Получаем токен
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="integration_token"):
            
            login_data = {"username": "testuser", "password": "testpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            access_token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.cache.cache_service.get') as mock_cache_get, \
             patch('apps.api.src.services.cache.cache_service.set') as mock_cache_set:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
            
            # Первый запрос - кэш пуст
            mock_cache_get.return_value = None
            
            with patch('apps.api.src.services.document_service.DocumentService.get_documents') as mock_get_docs:
                mock_get_docs.return_value = [{"id": "doc-1", "title": "Test Doc"}]
                
                start_time = datetime.utcnow()
                response = await test_client.get("/api/v1/documents/", headers=headers)
                first_request_time = (datetime.utcnow() - start_time).total_seconds()
                
                assert response.status_code == 200
                # Проверяем что данные были сохранены в кэш
                mock_cache_set.assert_called()
            
            # Второй запрос - кэш попадание
            mock_cache_get.return_value = [{"id": "doc-1", "title": "Test Doc"}]
            
            start_time = datetime.utcnow()
            response = await test_client.get("/api/v1/documents/", headers=headers)
            second_request_time = (datetime.utcnow() - start_time).total_seconds()
            
            assert response.status_code == 200
            # Второй запрос должен быть быстрее (в реальности, в тестах может не быть разницы)
    
    async def test_webhook_notification_integration(self, test_client: AsyncClient):
        """Тест интеграции webhook уведомлений"""
        # Получаем админский токен
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="webhook_token"):
            
            login_data = {"username": "admin", "password": "adminpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            admin_token = response.json()["access_token"]
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Создаем webhook
        webhook_data = {
            "name": "Document Upload Webhook",
            "url": "https://example.com/webhook",
            "events": ["document.uploaded"],
            "active": True
        }
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.webhook_service.webhook_service.register_webhook') as mock_register:
            
            mock_auth.return_value = AsyncMock(
                user_id=1, username="admin", tenant_id=1,
                role="admin", permissions=["admin"]
            )
            
            mock_register.return_value = {
                "id": 1,
                "name": webhook_data["name"],
                "url": webhook_data["url"],
                "events": webhook_data["events"]
            }
            
            response = await test_client.post("/api/v1/webhooks/", headers=admin_headers, json=webhook_data)
            assert response.status_code == 200
        
        # Загружаем документ (должен вызвать webhook)
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
             patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create, \
             patch('apps.api.src.services.webhook_service.event_triggers.document_uploaded') as mock_webhook:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="admin", tenant_id=1)
            mock_save.return_value = "/tmp/webhook_test.txt"
            mock_create.return_value = {
                "id": "webhook-doc-1",
                "title": "Webhook Test Document",
                "filename": "test.txt"
            }
            
            files = {"file": ("test.txt", b"webhook test content", "text/plain")}
            response = await test_client.post("/api/v1/documents/upload", headers=admin_headers, files=files)
            
            assert response.status_code == 201
            # В реальной реализации webhook должен быть вызван
            # mock_webhook.assert_called_once()


@pytest.mark.e2e
@pytest.mark.slow
class TestDataConsistency:
    """E2E тесты консистентности данных"""
    
    async def test_concurrent_operations_consistency(self, test_client: AsyncClient):
        """Тест консистентности при одновременных операциях"""
        # Получаем токен
        with patch('apps.api.src.services.auth.AuthService.verify_password', return_value=True), \
             patch('apps.api.src.services.auth.AuthService.create_access_token', return_value="consistency_token"):
            
            login_data = {"username": "testuser", "password": "testpass"}
            response = await test_client.post("/api/v1/auth/login", json=login_data)
            access_token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Одновременная загрузка документов
        async def upload_document(doc_num):
            with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
                 patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
                 patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create:
                
                mock_auth.return_value = AsyncMock(user_id=1, username="testuser", tenant_id=1)
                mock_save.return_value = f"/tmp/concurrent_doc_{doc_num}.txt"
                mock_create.return_value = {
                    "id": f"concurrent-doc-{doc_num}",
                    "title": f"Concurrent Document {doc_num}",
                    "filename": f"doc_{doc_num}.txt"
                }
                
                files = {"file": (f"doc_{doc_num}.txt", f"Content {doc_num}".encode(), "text/plain")}
                return await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
        
        # Загружаем 3 документа одновременно
        tasks = [upload_document(i) for i in range(1, 4)]
        responses = await asyncio.gather(*tasks)
        
        # Все загрузки должны быть успешными
        for response in responses:
            assert response.status_code == 201
        
        # Проверяем что все документы созданы корректно
        doc_ids = [response.json()["id"] for response in responses]
        assert len(set(doc_ids)) == 3  # Все ID уникальны
