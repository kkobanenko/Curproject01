"""
Нагрузочные тесты для проверки производительности системы
"""
import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from ...main import app


@pytest.mark.load
@pytest.mark.slow
class TestAPILoadTesting:
    """Нагрузочные тесты API эндпоинтов"""
    
    async def test_concurrent_search_requests(self, test_client: AsyncClient):
        """Тест одновременных поисковых запросов"""
        # Настройка аутентификации
        auth_token = "load_test_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Подготавливаем моки
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="loadtest", tenant_id=1)
            mock_search.return_value = {
                "results": [
                    {"chunk_id": "chunk-1", "content": "Test result", "score": 0.9}
                ],
                "total": 1,
                "query_time_ms": 100.0
            }
            
            # Функция для выполнения одного поискового запроса
            async def single_search_request(request_id: int):
                search_data = {
                    "query": f"test query {request_id}",
                    "search_type": "semantic",
                    "limit": 10
                }
                
                start_time = time.time()
                response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
                end_time = time.time()
                
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "timestamp": datetime.utcnow()
                }
            
            # Параметры нагрузочного теста
            concurrent_requests = 50
            total_requests = 200
            
            # Выполняем тест волнами по 50 одновременных запросов
            all_results = []
            
            for wave in range(total_requests // concurrent_requests):
                wave_start = time.time()
                
                # Создаем задачи для текущей волны
                tasks = [
                    single_search_request(wave * concurrent_requests + i)
                    for i in range(concurrent_requests)
                ]
                
                # Выполняем все запросы волны одновременно
                wave_results = await asyncio.gather(*tasks)
                all_results.extend(wave_results)
                
                wave_end = time.time()
                wave_duration = wave_end - wave_start
                
                print(f"Wave {wave + 1}: {concurrent_requests} requests in {wave_duration:.2f}s")
                
                # Небольшая пауза между волнами
                await asyncio.sleep(0.1)
            
            # Анализ результатов
            response_times = [r["response_time"] for r in all_results]
            success_count = sum(1 for r in all_results if r["status_code"] == 200)
            
            # Статистика производительности
            stats = {
                "total_requests": len(all_results),
                "successful_requests": success_count,
                "success_rate": (success_count / len(all_results)) * 100,
                "avg_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)],
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "requests_per_second": len(all_results) / sum(response_times)
            }
            
            # Выводим статистику
            print(f"\n=== LOAD TEST RESULTS ===")
            print(f"Total requests: {stats['total_requests']}")
            print(f"Success rate: {stats['success_rate']:.1f}%")
            print(f"Average response time: {stats['avg_response_time']:.3f}s")
            print(f"95th percentile: {stats['p95_response_time']:.3f}s")
            print(f"99th percentile: {stats['p99_response_time']:.3f}s")
            print(f"Requests per second: {stats['requests_per_second']:.1f}")
            
            # Assertions для проверки производительности
            assert stats["success_rate"] >= 95.0, f"Success rate {stats['success_rate']:.1f}% below 95%"
            assert stats["avg_response_time"] <= 2.0, f"Average response time {stats['avg_response_time']:.3f}s exceeds 2s"
            assert stats["p95_response_time"] <= 5.0, f"95th percentile {stats['p95_response_time']:.3f}s exceeds 5s"
    
    async def test_document_upload_load(self, test_client: AsyncClient):
        """Тест нагрузки при загрузке документов"""
        auth_token = "upload_load_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth, \
             patch('apps.api.src.services.document_service.DocumentService.save_uploaded_file') as mock_save, \
             patch('apps.api.src.services.document_service.DocumentService.create_document') as mock_create:
            
            mock_auth.return_value = AsyncMock(user_id=1, username="uploadtest", tenant_id=1)
            
            async def single_upload_request(doc_id: int):
                mock_save.return_value = f"/tmp/load_test_doc_{doc_id}.txt"
                mock_create.return_value = {
                    "id": f"load-doc-{doc_id}",
                    "title": f"Load Test Document {doc_id}",
                    "filename": f"doc_{doc_id}.txt"
                }
                
                # Создаем тестовый файл
                test_content = f"This is load test document {doc_id} " * 100  # ~3KB файл
                files = {"file": (f"doc_{doc_id}.txt", test_content.encode(), "text/plain")}
                
                start_time = time.time()
                response = await test_client.post("/api/v1/documents/upload", headers=headers, files=files)
                end_time = time.time()
                
                return {
                    "doc_id": doc_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "file_size": len(test_content)
                }
            
            # Параметры теста загрузки
            concurrent_uploads = 10
            total_uploads = 50
            
            all_results = []
            
            for batch in range(total_uploads // concurrent_uploads):
                batch_start = time.time()
                
                tasks = [
                    single_upload_request(batch * concurrent_uploads + i)
                    for i in range(concurrent_uploads)
                ]
                
                batch_results = await asyncio.gather(*tasks)
                all_results.extend(batch_results)
                
                batch_end = time.time()
                print(f"Upload batch {batch + 1}: {concurrent_uploads} uploads in {batch_end - batch_start:.2f}s")
                
                await asyncio.sleep(0.2)  # Пауза между батчами
            
            # Анализ результатов загрузки
            upload_times = [r["response_time"] for r in all_results]
            success_count = sum(1 for r in all_results if r["status_code"] == 201)
            
            upload_stats = {
                "total_uploads": len(all_results),
                "successful_uploads": success_count,
                "success_rate": (success_count / len(all_results)) * 100,
                "avg_upload_time": statistics.mean(upload_times),
                "max_upload_time": max(upload_times),
                "uploads_per_second": len(all_results) / sum(upload_times)
            }
            
            print(f"\n=== UPLOAD LOAD TEST RESULTS ===")
            print(f"Total uploads: {upload_stats['total_uploads']}")
            print(f"Success rate: {upload_stats['success_rate']:.1f}%")
            print(f"Average upload time: {upload_stats['avg_upload_time']:.3f}s")
            print(f"Max upload time: {upload_stats['max_upload_time']:.3f}s")
            
            assert upload_stats["success_rate"] >= 90.0
            assert upload_stats["avg_upload_time"] <= 3.0
    
    async def test_mixed_workload_stress(self, test_client: AsyncClient):
        """Тест смешанной нагрузки (поиск + загрузка + RAG)"""
        auth_token = "stress_test_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(user_id=1, username="stresstest", tenant_id=1)
            
            # Функции для разных типов запросов
            async def search_request(request_id: int):
                with patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
                    mock_search.return_value = {"results": [], "total": 0, "query_time_ms": 50.0}
                    
                    search_data = {"query": f"stress test {request_id}", "search_type": "semantic"}
                    start_time = time.time()
                    response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
                    
                    return {
                        "type": "search",
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response_time": time.time() - start_time
                    }
            
            async def rag_request(request_id: int):
                with patch('apps.api.src.services.rag_service.RAGService.generate_answer') as mock_rag:
                    mock_rag.return_value = {
                        "answer": "Test RAG answer",
                        "sources": [],
                        "confidence_score": 0.8,
                        "processing_time_ms": 200.0
                    }
                    
                    rag_data = {"question": f"What is stress test {request_id}?"}
                    start_time = time.time()
                    response = await test_client.post("/api/v1/answers/rag", headers=headers, json=rag_data)
                    
                    return {
                        "type": "rag",
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response_time": time.time() - start_time
                    }
            
            async def document_list_request(request_id: int):
                with patch('apps.api.src.services.document_service.DocumentService.get_documents') as mock_docs:
                    mock_docs.return_value = [{"id": f"doc-{i}", "title": f"Doc {i}"} for i in range(10)]
                    
                    start_time = time.time()
                    response = await test_client.get("/api/v1/documents/", headers=headers)
                    
                    return {
                        "type": "document_list",
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response_time": time.time() - start_time
                    }
            
            # Создаем смешанную нагрузку
            stress_tasks = []
            
            # 40% поисковых запросов
            for i in range(40):
                stress_tasks.append(search_request(i))
            
            # 30% RAG запросов
            for i in range(30):
                stress_tasks.append(rag_request(i))
            
            # 30% запросов списка документов
            for i in range(30):
                stress_tasks.append(document_list_request(i))
            
            # Перемешиваем задачи
            import random
            random.shuffle(stress_tasks)
            
            # Выполняем все задачи одновременно
            stress_start = time.time()
            stress_results = await asyncio.gather(*stress_tasks)
            stress_duration = time.time() - stress_start
            
            # Анализ результатов стресс-теста
            by_type = {}
            for result in stress_results:
                req_type = result["type"]
                if req_type not in by_type:
                    by_type[req_type] = []
                by_type[req_type].append(result)
            
            print(f"\n=== STRESS TEST RESULTS ===")
            print(f"Total duration: {stress_duration:.2f}s")
            print(f"Total requests: {len(stress_results)}")
            print(f"Requests per second: {len(stress_results) / stress_duration:.1f}")
            
            for req_type, results in by_type.items():
                success_count = sum(1 for r in results if r["status_code"] in [200, 201])
                avg_time = statistics.mean([r["response_time"] for r in results])
                
                print(f"{req_type}: {len(results)} requests, "
                      f"{(success_count/len(results)*100):.1f}% success, "
                      f"{avg_time:.3f}s avg")
            
            # Общие assertions
            overall_success = sum(1 for r in stress_results if r["status_code"] in [200, 201])
            success_rate = (overall_success / len(stress_results)) * 100
            
            assert success_rate >= 85.0, f"Overall success rate {success_rate:.1f}% below 85%"
            assert len(stress_results) / stress_duration >= 10.0, "Less than 10 requests per second"


@pytest.mark.load
class TestDatabaseLoadTesting:
    """Нагрузочные тесты базы данных"""
    
    async def test_concurrent_database_operations(self, db_connection):
        """Тест одновременных операций с базой данных"""
        
        async def concurrent_insert(batch_id: int, batch_size: int = 10):
            """Вставка батча записей"""
            start_time = time.time()
            
            for i in range(batch_size):
                await db_connection.execute("""
                    INSERT INTO search_queries (user_id, tenant_id, query_text, query_type, results_count)
                    VALUES ($1, $2, $3, $4, $5)
                """, 1, 1, f"load test query {batch_id}-{i}", "semantic", i)
            
            return {
                "batch_id": batch_id,
                "batch_size": batch_size,
                "duration": time.time() - start_time
            }
        
        async def concurrent_select(batch_id: int):
            """Чтение данных"""
            start_time = time.time()
            
            results = await db_connection.fetch("""
                SELECT * FROM search_queries 
                WHERE user_id = $1 AND tenant_id = $2
                ORDER BY created_at DESC
                LIMIT 100
            """, 1, 1)
            
            return {
                "batch_id": batch_id,
                "results_count": len(results),
                "duration": time.time() - start_time
            }
        
        # Создаем смешанную нагрузку на БД
        db_tasks = []
        
        # 60% операций вставки
        for i in range(30):
            db_tasks.append(concurrent_insert(i))
        
        # 40% операций чтения
        for i in range(20):
            db_tasks.append(concurrent_select(i))
        
        # Выполняем все операции одновременно
        db_start = time.time()
        db_results = await asyncio.gather(*db_tasks)
        db_duration = time.time() - db_start
        
        # Анализ результатов БД нагрузки
        insert_results = [r for r in db_results if "batch_size" in r]
        select_results = [r for r in db_results if "results_count" in r]
        
        total_inserts = sum(r["batch_size"] for r in insert_results)
        avg_insert_time = statistics.mean([r["duration"] for r in insert_results])
        avg_select_time = statistics.mean([r["duration"] for r in select_results])
        
        print(f"\n=== DATABASE LOAD TEST RESULTS ===")
        print(f"Total duration: {db_duration:.2f}s")
        print(f"Total insert operations: {len(insert_results)} batches, {total_inserts} records")
        print(f"Total select operations: {len(select_results)}")
        print(f"Average insert batch time: {avg_insert_time:.3f}s")
        print(f"Average select time: {avg_select_time:.3f}s")
        print(f"Inserts per second: {total_inserts / db_duration:.1f}")
        
        # Проверки производительности БД
        assert avg_insert_time <= 1.0, f"Insert batch time {avg_insert_time:.3f}s too slow"
        assert avg_select_time <= 0.5, f"Select time {avg_select_time:.3f}s too slow"
        assert total_inserts / db_duration >= 50.0, "Less than 50 inserts per second"


@pytest.mark.load
class TestCacheLoadTesting:
    """Нагрузочные тесты кэширования"""
    
    async def test_cache_performance_under_load(self, redis_client):
        """Тест производительности кэша под нагрузкой"""
        
        async def cache_write_operations(batch_id: int, batch_size: int = 100):
            """Операции записи в кэш"""
            start_time = time.time()
            
            for i in range(batch_size):
                key = f"load_test:{batch_id}:{i}"
                value = {"data": f"test data {batch_id}-{i}", "timestamp": time.time()}
                await redis_client.setex(key, 300, json.dumps(value))  # TTL 5 минут
            
            return {
                "batch_id": batch_id,
                "operation": "write",
                "batch_size": batch_size,
                "duration": time.time() - start_time
            }
        
        async def cache_read_operations(batch_id: int, batch_size: int = 100):
            """Операции чтения из кэша"""
            start_time = time.time()
            hits = 0
            
            for i in range(batch_size):
                key = f"load_test:{batch_id}:{i}"
                value = await redis_client.get(key)
                if value:
                    hits += 1
            
            return {
                "batch_id": batch_id,
                "operation": "read",
                "batch_size": batch_size,
                "hits": hits,
                "hit_rate": (hits / batch_size) * 100,
                "duration": time.time() - start_time
            }
        
        # Сначала записываем данные в кэш
        write_tasks = [cache_write_operations(i) for i in range(10)]
        write_results = await asyncio.gather(*write_tasks)
        
        # Затем читаем данные
        read_tasks = [cache_read_operations(i) for i in range(10)]
        read_results = await asyncio.gather(*read_tasks)
        
        # Анализ результатов кэша
        total_writes = sum(r["batch_size"] for r in write_results)
        total_reads = sum(r["batch_size"] for r in read_results)
        total_hits = sum(r["hits"] for r in read_results)
        
        avg_write_time = statistics.mean([r["duration"] for r in write_results])
        avg_read_time = statistics.mean([r["duration"] for r in read_results])
        overall_hit_rate = (total_hits / total_reads) * 100
        
        write_ops_per_sec = total_writes / sum(r["duration"] for r in write_results)
        read_ops_per_sec = total_reads / sum(r["duration"] for r in read_results)
        
        print(f"\n=== CACHE LOAD TEST RESULTS ===")
        print(f"Write operations: {total_writes} in {avg_write_time:.3f}s avg per batch")
        print(f"Read operations: {total_reads} in {avg_read_time:.3f}s avg per batch")
        print(f"Cache hit rate: {overall_hit_rate:.1f}%")
        print(f"Write ops/second: {write_ops_per_sec:.1f}")
        print(f"Read ops/second: {read_ops_per_sec:.1f}")
        
        # Проверки производительности кэша
        assert overall_hit_rate >= 95.0, f"Cache hit rate {overall_hit_rate:.1f}% too low"
        assert write_ops_per_sec >= 500.0, f"Write performance {write_ops_per_sec:.1f} ops/s too low"
        assert read_ops_per_sec >= 1000.0, f"Read performance {read_ops_per_sec:.1f} ops/s too low"


@pytest.mark.load
class TestMemoryAndResourceTesting:
    """Тесты использования памяти и ресурсов"""
    
    async def test_memory_usage_under_load(self, test_client: AsyncClient):
        """Тест использования памяти под нагрузкой"""
        import psutil
        import gc
        
        process = psutil.Process()
        
        # Измеряем начальное использование памяти
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        auth_token = "memory_test_token"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        with patch('apps.api.src.middleware.auth.AuthService.get_user_context_from_token') as mock_auth:
            mock_auth.return_value = AsyncMock(user_id=1, username="memorytest", tenant_id=1)
            
            # Создаем большое количество запросов для нагрузки на память
            async def memory_intensive_request(request_id: int):
                # Создаем запрос с большим количеством данных
                large_query = "memory test " * 1000  # 12KB строка
                search_data = {
                    "query": large_query,
                    "search_type": "semantic",
                    "limit": 100
                }
                
                with patch('apps.api.src.services.search_service.SearchService.semantic_search') as mock_search:
                    # Возвращаем большой результат
                    mock_search.return_value = {
                        "results": [
                            {"chunk_id": f"chunk-{i}", "content": "large content " * 100}
                            for i in range(50)
                        ],
                        "total": 50,
                        "query_time_ms": 100.0
                    }
                    
                    response = await test_client.post("/api/v1/search/semantic", headers=headers, json=search_data)
                    return response.status_code
            
            # Выполняем 100 запросов с большими данными
            memory_tasks = [memory_intensive_request(i) for i in range(100)]
            results = await asyncio.gather(*memory_tasks)
            
            # Принудительная сборка мусора
            gc.collect()
            
            # Измеряем использование памяти после нагрузки
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"\n=== MEMORY USAGE TEST RESULTS ===")
            print(f"Initial memory: {initial_memory:.1f} MB")
            print(f"Final memory: {final_memory:.1f} MB")
            print(f"Memory increase: {memory_increase:.1f} MB")
            print(f"Memory per request: {memory_increase / len(results):.3f} MB")
            
            # Проверки использования памяти
            success_count = sum(1 for status in results if status == 200)
            assert success_count == len(results), "Not all requests successful"
            
            # Память не должна увеличиваться более чем на 500MB
            assert memory_increase <= 500.0, f"Memory increase {memory_increase:.1f}MB too high"
            
            # Память на запрос не должна превышать 5MB
            memory_per_request = memory_increase / len(results)
            assert memory_per_request <= 5.0, f"Memory per request {memory_per_request:.3f}MB too high"
