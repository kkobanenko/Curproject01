"""
Unit тесты для системы мониторинга производительности
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from collections import deque

from ...services.performance_monitor import (
    PerformanceMetric, EndpointMetrics, PerformanceProfiler,
    PerformanceMiddleware, performance_timer, SystemMetricsCollector,
    profiler
)


@pytest.mark.unit
class TestPerformanceMetric:
    """Тесты для класса PerformanceMetric"""
    
    def test_performance_metric_creation(self):
        """Тест создания метрики производительности"""
        name = "test_metric"
        value = 123.45
        unit = "seconds"
        timestamp = datetime.utcnow()
        tags = {"endpoint": "/api/test"}
        metadata = {"user_id": 123}
        
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=timestamp,
            tags=tags,
            metadata=metadata
        )
        
        assert metric.name == name
        assert metric.value == value
        assert metric.unit == unit
        assert metric.timestamp == timestamp
        assert metric.tags == tags
        assert metric.metadata == metadata
    
    def test_performance_metric_defaults(self):
        """Тест значений по умолчанию"""
        metric = PerformanceMetric(
            name="test",
            value=1.0,
            unit="count",
            timestamp=datetime.utcnow()
        )
        
        assert metric.tags == {}
        assert metric.metadata == {}


@pytest.mark.unit
class TestEndpointMetrics:
    """Тесты для класса EndpointMetrics"""
    
    def test_endpoint_metrics_creation(self):
        """Тест создания метрик эндпоинта"""
        endpoint = "/api/test"
        method = "POST"
        
        metrics = EndpointMetrics(endpoint=endpoint, method=method)
        
        assert metrics.endpoint == endpoint
        assert metrics.method == method
        assert metrics.error_count == 0
        assert metrics.total_requests == 0
        assert metrics.last_request is None
        assert isinstance(metrics.response_times, deque)
        assert isinstance(metrics.status_codes, dict)
    
    def test_add_request_success(self):
        """Тест добавления успешного запроса"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        
        response_time = 0.150
        status_code = 200
        
        metrics.add_request(response_time, status_code)
        
        assert metrics.total_requests == 1
        assert metrics.error_count == 0
        assert len(metrics.response_times) == 1
        assert metrics.response_times[0] == response_time
        assert metrics.status_codes[200] == 1
        assert metrics.last_request is not None
    
    def test_add_request_error(self):
        """Тест добавления запроса с ошибкой"""
        metrics = EndpointMetrics(endpoint="/api/test", method="POST")
        
        response_time = 2.5
        status_code = 500
        
        metrics.add_request(response_time, status_code)
        
        assert metrics.total_requests == 1
        assert metrics.error_count == 1
        assert metrics.status_codes[500] == 1
    
    def test_avg_response_time(self):
        """Тест вычисления среднего времени ответа"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        
        # Добавляем несколько запросов
        times = [0.1, 0.2, 0.3, 0.4, 0.5]
        for time_val in times:
            metrics.add_request(time_val, 200)
        
        expected_avg = sum(times) / len(times)
        assert abs(metrics.avg_response_time - expected_avg) < 0.001
    
    def test_avg_response_time_empty(self):
        """Тест среднего времени для пустых метрик"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        assert metrics.avg_response_time == 0.0
    
    def test_p95_response_time(self):
        """Тест вычисления 95-го процентиля"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        
        # Добавляем 20 запросов с возрастающим временем
        times = [i * 0.1 for i in range(1, 21)]  # 0.1, 0.2, ..., 2.0
        for time_val in times:
            metrics.add_request(time_val, 200)
        
        p95 = metrics.p95_response_time
        # 95% от 20 запросов = 19-й элемент (индекс 18)
        expected_p95 = 1.9
        assert abs(p95 - expected_p95) < 0.001
    
    def test_error_rate(self):
        """Тест вычисления процента ошибок"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        
        # Добавляем 10 запросов: 8 успешных, 2 с ошибками
        for _ in range(8):
            metrics.add_request(0.1, 200)
        for _ in range(2):
            metrics.add_request(0.1, 500)
        
        assert metrics.error_rate == 20.0  # 2/10 * 100
    
    def test_error_rate_no_requests(self):
        """Тест процента ошибок без запросов"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        assert metrics.error_rate == 0.0
    
    def test_response_times_max_length(self):
        """Тест ограничения размера очереди времен ответа"""
        metrics = EndpointMetrics(endpoint="/api/test", method="GET")
        
        # Добавляем больше запросов чем максимальный размер очереди (1000)
        for i in range(1500):
            metrics.add_request(0.1, 200)
        
        # Очередь должна содержать только последние 1000 запросов
        assert len(metrics.response_times) == 1000
        assert metrics.total_requests == 1500


@pytest.mark.unit
class TestPerformanceProfiler:
    """Тесты для профилировщика производительности"""
    
    @pytest.fixture
    def profiler_instance(self):
        """Создание экземпляра профилировщика"""
        return PerformanceProfiler()
    
    def test_record_metric(self, profiler_instance):
        """Тест записи метрики"""
        name = "test_metric"
        value = 42.0
        unit = "count"
        tags = {"component": "test"}
        metadata = {"version": "1.0"}
        
        profiler_instance.record_metric(name, value, unit, tags, metadata)
        
        assert len(profiler_instance.metrics) == 1
        
        metric = profiler_instance.metrics[0]
        assert metric.name == name
        assert metric.value == value
        assert metric.unit == unit
        assert metric.tags == tags
        assert metric.metadata == metadata
    
    def test_record_request(self, profiler_instance):
        """Тест записи HTTP запроса"""
        endpoint = "/api/test"
        method = "GET"
        response_time = 0.250
        status_code = 200
        user_id = 123
        
        profiler_instance.record_request(
            endpoint, method, response_time, status_code, user_id
        )
        
        endpoint_key = f"{method} {endpoint}"
        assert endpoint_key in profiler_instance.endpoint_metrics
        
        endpoint_metrics = profiler_instance.endpoint_metrics[endpoint_key]
        assert endpoint_metrics.total_requests == 1
        assert endpoint_metrics.response_times[0] == response_time
        
        # Проверяем что записана общая метрика
        http_metrics = [m for m in profiler_instance.metrics if m.name == "http_request_duration"]
        assert len(http_metrics) == 1
        assert http_metrics[0].value == response_time
    
    def test_record_slow_request_logging(self, profiler_instance):
        """Тест логирования медленных запросов"""
        profiler_instance.slow_request_threshold = 1.0
        
        with patch('apps.api.src.services.performance_monitor.logger') as mock_logger:
            profiler_instance.record_request(
                "/api/slow", "POST", 2.5, 200  # Медленный запрос
            )
            
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "Slow request" in warning_message
            assert "2.500s" in warning_message
    
    def test_record_database_query(self, profiler_instance):
        """Тест записи метрики запроса к БД"""
        query_hash = "abc123"
        execution_time = 0.050
        rows_affected = 10
        query_type = "SELECT"
        
        profiler_instance.record_database_query(
            query_hash, execution_time, rows_affected, query_type
        )
        
        db_metrics = [m for m in profiler_instance.metrics if m.name == "database_query_duration"]
        assert len(db_metrics) == 1
        
        metric = db_metrics[0]
        assert metric.value == execution_time
        assert metric.tags["query_hash"] == query_hash
        assert metric.tags["query_type"] == query_type
        assert metric.metadata["rows_affected"] == rows_affected
    
    def test_record_cache_operation(self, profiler_instance):
        """Тест записи операции кэша"""
        operation = "get"
        hit = True
        duration = 0.001
        key_pattern = "user:*"
        
        profiler_instance.record_cache_operation(operation, hit, duration, key_pattern)
        
        # Проверяем метрику времени операции
        duration_metrics = [m for m in profiler_instance.metrics if m.name == "cache_operation_duration"]
        assert len(duration_metrics) == 1
        assert duration_metrics[0].value == duration
        
        # Проверяем метрику hit/miss
        hit_metrics = [m for m in profiler_instance.metrics if m.name == "cache_hit"]
        assert len(hit_metrics) == 1
        assert hit_metrics[0].value == 1.0  # hit = True
    
    def test_record_system_metrics(self, profiler_instance):
        """Тест записи системных метрик"""
        with patch('psutil.cpu_percent', return_value=45.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process:
            
            # Настраиваем моки
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.available = 2048000000
            
            mock_disk.return_value.percent = 30.0
            mock_disk.return_value.free = 10000000000
            
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value.rss = 104857600
            mock_process_instance.cpu_percent.return_value = 5.0
            mock_process_instance.num_threads.return_value = 4
            mock_process.return_value = mock_process_instance
            
            profiler_instance.record_system_metrics()
            
            # Проверяем что записаны системные метрики
            metric_names = [m.name for m in profiler_instance.metrics]
            expected_metrics = [
                "system_cpu_usage",
                "system_memory_usage",
                "system_memory_available",
                "system_disk_usage",
                "system_disk_free",
                "process_memory_rss",
                "process_cpu_percent",
                "process_num_threads"
            ]
            
            for expected_metric in expected_metrics:
                assert expected_metric in metric_names
    
    def test_check_alert_thresholds(self, profiler_instance):
        """Тест проверки порогов алертов"""
        # Устанавливаем низкий порог для тестирования
        profiler_instance.alert_thresholds["memory_usage"] = 50.0
        
        with patch('apps.api.src.services.performance_monitor.logger') as mock_logger:
            # Записываем метрику, превышающую порог
            profiler_instance.record_metric("system_memory_usage", 75.0, "percent")
            
            # Проверяем что создан алерт
            assert profiler_instance.alert_counters["memory_usage"] == 1
            mock_logger.warning.assert_called_once()
    
    def test_alert_rate_limiting(self, profiler_instance):
        """Тест ограничения частоты алертов"""
        profiler_instance.alert_thresholds["cpu_usage"] = 50.0
        
        with patch('apps.api.src.services.performance_monitor.logger') as mock_logger:
            # Первый алерт должен пройти
            profiler_instance.record_metric("system_cpu_usage", 80.0, "percent")
            assert mock_logger.warning.call_count == 1
            
            # Второй алерт сразу же не должен пройти (rate limiting)
            profiler_instance.record_metric("system_cpu_usage", 85.0, "percent")
            assert mock_logger.warning.call_count == 1  # Не увеличился
    
    def test_get_endpoint_stats(self, profiler_instance):
        """Тест получения статистики эндпоинтов"""
        # Добавляем данные в несколько эндпоинтов
        endpoints = [
            ("/api/users", "GET", 10, 0.1),
            ("/api/documents", "POST", 5, 0.5),
            ("/api/search", "POST", 15, 0.3)
        ]
        
        for endpoint, method, requests, avg_time in endpoints:
            for _ in range(requests):
                profiler_instance.record_request(endpoint, method, avg_time, 200)
        
        stats = profiler_instance.get_endpoint_stats(limit=10)
        
        assert len(stats) == 3
        # Проверяем что отсортировано по количеству запросов (убывание)
        assert stats[0]["total_requests"] >= stats[1]["total_requests"]
        assert stats[1]["total_requests"] >= stats[2]["total_requests"]
        
        # Проверяем структуру статистики
        for stat in stats:
            required_fields = [
                "endpoint", "method", "total_requests", "avg_response_time",
                "p95_response_time", "error_rate", "requests_per_minute", "status_codes"
            ]
            for field in required_fields:
                assert field in stat
    
    def test_get_slow_endpoints(self, profiler_instance):
        """Тест получения медленных эндпоинтов"""
        # Добавляем эндпоинты с разным временем ответа
        endpoints = [
            ("/api/fast", "GET", 0.1),
            ("/api/medium", "GET", 0.5),
            ("/api/slow", "GET", 2.0)
        ]
        
        for endpoint, method, response_time in endpoints:
            profiler_instance.record_request(endpoint, method, response_time, 200)
        
        slow_endpoints = profiler_instance.get_slow_endpoints(limit=2)
        
        assert len(slow_endpoints) == 2
        # Проверяем что отсортировано по времени ответа (убывание)
        assert slow_endpoints[0]["p95_response_time"] >= slow_endpoints[1]["p95_response_time"]
    
    def test_get_error_prone_endpoints(self, profiler_instance):
        """Тест получения эндпоинтов с ошибками"""
        # Добавляем эндпоинты с разным процентом ошибок
        profiler_instance.record_request("/api/good", "GET", 0.1, 200)
        profiler_instance.record_request("/api/good", "GET", 0.1, 200)
        
        profiler_instance.record_request("/api/bad", "GET", 0.1, 200)
        profiler_instance.record_request("/api/bad", "GET", 0.1, 500)
        
        error_endpoints = profiler_instance.get_error_prone_endpoints(limit=5)
        
        # Должен быть только один эндпоинт с ошибками
        assert len(error_endpoints) == 1
        assert error_endpoints[0]["endpoint"] == "/api/bad"
        assert error_endpoints[0]["error_rate"] == 50.0
    
    def test_get_performance_summary(self, profiler_instance):
        """Тест получения сводки производительности"""
        # Добавляем тестовые данные
        profiler_instance.record_request("/api/test", "GET", 0.2, 200)
        profiler_instance.record_request("/api/test", "GET", 0.3, 500)
        profiler_instance.record_cache_operation("get", True, 0.001)
        profiler_instance.record_cache_operation("get", False, 0.002)
        
        summary = profiler_instance.get_performance_summary()
        
        required_fields = [
            "total_requests", "avg_response_time", "error_rate", 
            "cache_hit_rate", "system_status", "alerts_active"
        ]
        
        for field in required_fields:
            assert field in summary
        
        assert summary["total_requests"] == 2
        assert summary["error_rate"] == 50.0  # 1 из 2 запросов с ошибкой
        assert summary["cache_hit_rate"] == 50.0  # 1 из 2 hit
    
    def test_metrics_size_limit(self, profiler_instance):
        """Тест ограничения размера списка метрик"""
        profiler_instance.max_metrics = 5
        
        # Добавляем метрик больше лимита
        for i in range(10):
            profiler_instance.record_metric(f"metric_{i}", i, "count")
        
        # Должно остаться только 5 последних метрик
        assert len(profiler_instance.metrics) == 5
        assert profiler_instance.metrics[0].name == "metric_5"  # Первая из оставшихся
        assert profiler_instance.metrics[-1].name == "metric_9"  # Последняя
    
    def test_get_metrics_by_name(self, profiler_instance):
        """Тест получения метрик по названию"""
        # Добавляем различные метрики
        metric_names = ["cpu_usage", "memory_usage", "cpu_usage", "disk_usage"]
        for i, name in enumerate(metric_names):
            profiler_instance.record_metric(name, i * 10, "percent")
        
        cpu_metrics = profiler_instance.get_metrics_by_name("cpu_usage")
        
        assert len(cpu_metrics) == 2
        assert all(m.name == "cpu_usage" for m in cpu_metrics)
        # Проверяем что отсортировано по времени (новые первые)
        assert cpu_metrics[0].timestamp >= cpu_metrics[1].timestamp


@pytest.mark.unit
class TestPerformanceMiddleware:
    """Тесты для middleware мониторинга производительности"""
    
    @pytest.fixture
    def mock_profiler(self):
        """Mock профилировщика"""
        return MagicMock()
    
    @pytest.fixture
    def middleware(self, mock_profiler):
        """Экземпляр middleware"""
        return PerformanceMiddleware(mock_profiler)
    
    async def test_middleware_success_request(self, middleware, mock_profiler):
        """Тест успешного запроса через middleware"""
        # Mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/test"
        mock_request.state = MagicMock()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # Mock call_next
        async def mock_call_next(request):
            await asyncio.sleep(0.01)  # Имитируем время обработки
            return mock_response
        
        result = await middleware(mock_request, mock_call_next)
        
        assert result == mock_response
        
        # Проверяем что записаны метрики
        mock_profiler.record_request.assert_called_once()
        call_args = mock_profiler.record_request.call_args[1]
        assert call_args["endpoint"] == "/api/test"
        assert call_args["method"] == "GET"
        assert call_args["status_code"] == 200
        assert call_args["response_time"] > 0
    
    async def test_middleware_error_request(self, middleware, mock_profiler):
        """Тест запроса с ошибкой через middleware"""
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/error"
        mock_request.state = MagicMock()
        
        # Mock call_next выбрасывает исключение
        async def mock_call_next_error(request):
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await middleware(mock_request, mock_call_next_error)
        
        # Проверяем что записаны метрики ошибки
        mock_profiler.record_request.assert_called_once()
        call_args = mock_profiler.record_request.call_args[1]
        assert call_args["status_code"] == 500
        
        # Проверяем что записана метрика ошибки
        mock_profiler.record_metric.assert_called_once()
        error_metric_call = mock_profiler.record_metric.call_args
        assert error_metric_call[0][0] == "http_request_error"
        assert error_metric_call[1]["tags"]["error_type"] == "ValueError"
    
    async def test_middleware_with_user_context(self, middleware, mock_profiler):
        """Тест middleware с контекстом пользователя"""
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/user"
        mock_request.state.user = {"user_id": 123}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        async def mock_call_next(request):
            return mock_response
        
        await middleware(mock_request, mock_call_next)
        
        # Проверяем что user_id передан в метрики
        call_args = mock_profiler.record_request.call_args[1]
        assert call_args["user_id"] == 123


@pytest.mark.unit 
class TestPerformanceTimer:
    """Тесты для декоратора performance_timer"""
    
    async def test_timer_async_function_success(self):
        """Тест декоратора с успешной асинхронной функцией"""
        with patch.object(profiler, 'record_metric') as mock_record:
            @performance_timer("test_operation")
            async def async_function():
                await asyncio.sleep(0.01)
                return "result"
            
            result = await async_function()
            
            assert result == "result"
            mock_record.assert_called_once()
            
            call_args = mock_record.call_args
            assert call_args[0][0] == "test_operation"  # metric name
            assert call_args[0][2] == "seconds"  # unit
            assert call_args[1]["tags"]["function"] == "async_function"
            assert call_args[1]["tags"]["status"] == "success"
    
    async def test_timer_async_function_error(self):
        """Тест декоратора с асинхронной функцией, выбрасывающей ошибку"""
        with patch.object(profiler, 'record_metric') as mock_record:
            @performance_timer("test_operation")
            async def async_function_error():
                await asyncio.sleep(0.01)
                raise ValueError("Test error")
            
            with pytest.raises(ValueError):
                await async_function_error()
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[1]["tags"]["status"] == "error"
            assert call_args[1]["tags"]["error_type"] == "ValueError"
    
    def test_timer_sync_function_success(self):
        """Тест декоратора с успешной синхронной функцией"""
        with patch.object(profiler, 'record_metric') as mock_record:
            @performance_timer("sync_operation")
            def sync_function():
                time.sleep(0.01)
                return "sync_result"
            
            result = sync_function()
            
            assert result == "sync_result"
            mock_record.assert_called_once()
            
            call_args = mock_record.call_args
            assert call_args[0][0] == "sync_operation"
            assert call_args[1]["tags"]["function"] == "sync_function"
            assert call_args[1]["tags"]["status"] == "success"
    
    def test_timer_sync_function_error(self):
        """Тест декоратора с синхронной функцией, выбрасывающей ошибку"""
        with patch.object(profiler, 'record_metric') as mock_record:
            @performance_timer("sync_operation")
            def sync_function_error():
                time.sleep(0.01)
                raise RuntimeError("Sync error")
            
            with pytest.raises(RuntimeError):
                sync_function_error()
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[1]["tags"]["status"] == "error"
            assert call_args[1]["tags"]["error_type"] == "RuntimeError"


@pytest.mark.unit
class TestSystemMetricsCollector:
    """Тесты для сборщика системных метрик"""
    
    @pytest.fixture
    def mock_profiler(self):
        """Mock профилировщика"""
        return MagicMock()
    
    @pytest.fixture
    def collector(self, mock_profiler):
        """Экземпляр сборщика"""
        return SystemMetricsCollector(mock_profiler, interval=1)
    
    def test_collector_start_stop(self, collector):
        """Тест запуска и остановки сборщика"""
        assert not collector.running
        assert collector.thread is None
        
        collector.start()
        
        assert collector.running
        assert collector.thread is not None
        assert collector.thread.is_alive()
        
        collector.stop()
        
        assert not collector.running
    
    def test_collector_already_running(self, collector):
        """Тест повторного запуска уже работающего сборщика"""
        collector.start()
        first_thread = collector.thread
        
        collector.start()  # Повторный запуск
        
        # Поток должен остаться тем же
        assert collector.thread is first_thread
        
        collector.stop()
    
    @patch('time.sleep')
    def test_collect_loop_calls_profiler(self, mock_sleep, collector, mock_profiler):
        """Тест что цикл сбора вызывает профилировщик"""
        # Настраиваем sleep для выхода из цикла после первой итерации
        mock_sleep.side_effect = [None, KeyboardInterrupt()]
        
        collector.running = True
        
        try:
            collector._collect_loop()
        except KeyboardInterrupt:
            pass
        
        # Проверяем что вызван метод записи метрик
        mock_profiler.record_system_metrics.assert_called()
    
    @patch('time.sleep')
    def test_collect_loop_error_handling(self, mock_sleep, collector, mock_profiler):
        """Тест обработки ошибок в цикле сбора"""
        # Настраиваем профилировщик для выброса ошибки
        mock_profiler.record_system_metrics.side_effect = [Exception("Test error"), None]
        mock_sleep.side_effect = [None, None, KeyboardInterrupt()]
        
        collector.running = True
        
        try:
            collector._collect_loop()
        except KeyboardInterrupt:
            pass
        
        # Проверяем что цикл продолжился после ошибки
        assert mock_profiler.record_system_metrics.call_count == 2
