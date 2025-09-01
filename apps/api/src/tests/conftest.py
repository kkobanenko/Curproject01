"""
Конфигурация pytest для тестирования RAG Platform API
"""
import pytest
import asyncio
import asyncpg
from httpx import AsyncClient
from fastapi.testclient import TestClient
from typing import AsyncGenerator, Generator, Dict, Any
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Импорты приложения
from ..main import app
from ..settings import get_settings
from ..services.cache import cache_service, cache_manager
from ..services.database_optimizer import db_optimizer
from ..services.performance_monitor import profiler
from ..schemas.auth import User, UserRole, Permission


# Настройки для тестов
TEST_DATABASE_URL = "postgresql://test_user:test_pass@localhost:5432/test_rag_db"
TEST_REDIS_URL = "redis://localhost:6380/1"  # Используем другую БД для тестов


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для всей сессии тестов"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Создание тестовой базы данных"""
    # Создаем тестовую БД
    admin_conn = await asyncpg.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    
    try:
        await admin_conn.execute("DROP DATABASE IF EXISTS test_rag_db")
        await admin_conn.execute("CREATE DATABASE test_rag_db")
        yield TEST_DATABASE_URL
    finally:
        await admin_conn.execute("DROP DATABASE IF EXISTS test_rag_db")
        await admin_conn.close()


@pytest.fixture
async def db_connection(test_database):
    """Подключение к тестовой БД"""
    conn = await asyncpg.connect(test_database)
    
    # Создаем схему для тестов
    await conn.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            tenant_id INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(500) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            size_bytes INTEGER NOT NULL,
            user_id INTEGER REFERENCES users(id),
            tenant_id INTEGER DEFAULT 1,
            file_path VARCHAR(1000),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_type VARCHAR(50) DEFAULT 'text',
            metadata JSONB DEFAULT '{}',
            embedding vector(1536),
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS search_queries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER REFERENCES users(id),
            tenant_id INTEGER DEFAULT 1,
            query_text TEXT NOT NULL,
            query_type VARCHAR(50) DEFAULT 'semantic',
            results_count INTEGER DEFAULT 0,
            response_time_ms FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    yield conn
    await conn.close()


@pytest.fixture
async def redis_client():
    """Redis клиент для тестов"""
    import redis.asyncio as redis
    
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    
    # Очищаем тестовую БД Redis
    await client.flushdb()
    
    yield client
    
    # Очищаем после тестов
    await client.flushdb()
    await client.close()


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP клиент для тестирования API"""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sync_test_client() -> Generator[TestClient, None, None]:
    """Синхронный HTTP клиент для простых тестов"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def test_user(db_connection) -> User:
    """Создание тестового пользователя"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "$2b$12$example_hash",
        "role": "user",
        "tenant_id": 1
    }
    
    user_id = await db_connection.fetchval("""
        INSERT INTO users (username, email, hashed_password, role, tenant_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, user_data["username"], user_data["email"], user_data["hashed_password"], 
        user_data["role"], user_data["tenant_id"])
    
    return User(
        user_id=user_id,
        username=user_data["username"],
        email=user_data["email"],
        role=UserRole.USER,
        tenant_id=user_data["tenant_id"],
        permissions=[Permission.READ, Permission.WRITE],
        is_active=True
    )


@pytest.fixture
async def admin_user(db_connection) -> User:
    """Создание администратора"""
    admin_data = {
        "username": "admin",
        "email": "admin@example.com", 
        "hashed_password": "$2b$12$admin_hash",
        "role": "admin",
        "tenant_id": 1
    }
    
    admin_id = await db_connection.fetchval("""
        INSERT INTO users (username, email, hashed_password, role, tenant_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, admin_data["username"], admin_data["email"], admin_data["hashed_password"],
        admin_data["role"], admin_data["tenant_id"])
    
    return User(
        user_id=admin_id,
        username=admin_data["username"],
        email=admin_data["email"],
        role=UserRole.ADMIN,
        tenant_id=admin_data["tenant_id"],
        permissions=[Permission.ADMIN, Permission.READ, Permission.WRITE, Permission.DELETE],
        is_active=True
    )


@pytest.fixture
async def test_document(db_connection, test_user) -> Dict[str, Any]:
    """Создание тестового документа"""
    doc_data = {
        "title": "Test Document",
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "user_id": test_user.user_id,
        "tenant_id": test_user.tenant_id,
        "file_path": "/tmp/test.pdf",
        "metadata": {"author": "Test Author", "pages": 5}
    }
    
    doc_id = await db_connection.fetchval("""
        INSERT INTO documents (title, filename, content_type, size_bytes, user_id, tenant_id, file_path, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
    """, doc_data["title"], doc_data["filename"], doc_data["content_type"],
        doc_data["size_bytes"], doc_data["user_id"], doc_data["tenant_id"],
        doc_data["file_path"], doc_data["metadata"])
    
    doc_data["id"] = str(doc_id)
    return doc_data


@pytest.fixture
async def test_document_chunks(db_connection, test_document) -> list:
    """Создание чанков для тестового документа"""
    chunks_data = []
    
    for i in range(3):
        chunk_data = {
            "document_id": test_document["id"],
            "chunk_index": i,
            "content": f"This is test chunk {i} with some meaningful content for testing purposes.",
            "content_type": "text",
            "metadata": {"page": i + 1, "section": f"Section {i}"}
        }
        
        chunk_id = await db_connection.fetchval("""
            INSERT INTO document_chunks (document_id, chunk_index, content, content_type, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, chunk_data["document_id"], chunk_data["chunk_index"], 
            chunk_data["content"], chunk_data["content_type"], chunk_data["metadata"])
        
        chunk_data["id"] = str(chunk_id)
        chunks_data.append(chunk_data)
    
    return chunks_data


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama клиента"""
    mock_client = MagicMock()
    
    # Mock embeddings
    mock_client.embeddings.return_value = {
        "embedding": [0.1] * 1536  # Фиксированный эмбеддинг для тестов
    }
    
    # Mock chat completion
    mock_client.chat.return_value = {
        "message": {
            "content": "This is a test response from the mocked LLM."
        }
    }
    
    return mock_client


@pytest.fixture
def mock_redis_cache(redis_client):
    """Mock Redis кэша"""
    mock_cache = AsyncMock()
    
    # Словарь для имитации кэша
    cache_storage = {}
    
    async def mock_get(key, default=None):
        return cache_storage.get(key, default)
    
    async def mock_set(key, value, ttl=None):
        cache_storage[key] = value
        return True
    
    async def mock_delete(key):
        return cache_storage.pop(key, None) is not None
    
    async def mock_exists(key):
        return key in cache_storage
    
    mock_cache.get = mock_get
    mock_cache.set = mock_set
    mock_cache.delete = mock_delete
    mock_cache.exists = mock_exists
    
    return mock_cache


@pytest.fixture
def temp_file():
    """Временный файл для тестов"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(b"Test PDF content")
        temp_file_path = tmp.name
    
    yield temp_file_path
    
    # Очистка
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_jwt_token():
    """JWT токен для тестов"""
    # Простой тестовый токен
    return "test_jwt_token_12345"


@pytest.fixture
def mock_auth_service():
    """Mock сервиса аутентификации"""
    mock_service = MagicMock()
    
    mock_service.verify_token.return_value = True
    mock_service.get_user_from_token.return_value = {
        "user_id": 1,
        "username": "testuser",
        "role": "user",
        "tenant_id": 1
    }
    
    return mock_service


@pytest.fixture(scope="function")
async def clean_cache():
    """Очистка кэша между тестами"""
    # Очищаем перед тестом
    if hasattr(cache_service, 'redis_client') and cache_service.redis_client:
        try:
            await cache_service.redis_client.flushdb()
        except:
            pass
    
    yield
    
    # Очищаем после теста
    if hasattr(cache_service, 'redis_client') and cache_service.redis_client:
        try:
            await cache_service.redis_client.flushdb()
        except:
            pass


@pytest.fixture
def mock_file_upload():
    """Mock файла для загрузки"""
    from io import BytesIO
    from fastapi import UploadFile
    
    file_content = b"Test file content for upload testing"
    file_obj = BytesIO(file_content)
    
    return UploadFile(
        filename="test_upload.pdf",
        file=file_obj,
        size=len(file_content)
    )


@pytest.fixture
def performance_test_context():
    """Контекст для тестов производительности"""
    # Сбрасываем счетчики
    profiler.metrics.clear()
    profiler.endpoint_metrics.clear()
    
    yield profiler
    
    # Очищаем после тестов
    profiler.metrics.clear()
    profiler.endpoint_metrics.clear()


# Вспомогательные функции для тестов
class TestHelpers:
    """Вспомогательные функции для тестов"""
    
    @staticmethod
    async def create_test_embedding(dimension: int = 1536) -> list:
        """Создание тестового эмбеддинга"""
        import random
        return [random.random() for _ in range(dimension)]
    
    @staticmethod
    def assert_valid_uuid(uuid_string: str):
        """Проверка валидности UUID"""
        import uuid
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def assert_response_time(start_time: datetime, max_time_ms: int = 1000):
        """Проверка времени ответа"""
        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
        assert elapsed < max_time_ms, f"Response time {elapsed}ms exceeds {max_time_ms}ms"
    
    @staticmethod
    async def wait_for_async_task(task_func, timeout: int = 5):
        """Ожидание асинхронной задачи с таймаутом"""
        import asyncio
        try:
            return await asyncio.wait_for(task_func(), timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Task did not complete within {timeout} seconds")


# Создаем экземпляр помощников
helpers = TestHelpers()


# Маркеры для pytest
pytestmark = [
    pytest.mark.asyncio,
]


# Конфигурация pytest
def pytest_configure(config):
    """Конфигурация pytest"""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Модификация коллекции тестов"""
    for item in items:
        # Добавляем маркер unit по умолчанию если нет других маркеров
        if not any(mark.name in ["integration", "e2e", "performance"] for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Hooks для отчетности
@pytest.fixture(autouse=True)
def test_execution_time(request):
    """Автоматическое измерение времени выполнения тестов"""
    start_time = datetime.utcnow()
    
    yield
    
    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds()
    
    # Логируем медленные тесты
    if execution_time > 1.0:  # 1 секунда
        print(f"\n⚠️  Slow test: {request.node.name} took {execution_time:.3f}s")


# Настройки для тестовой среды
os.environ.update({
    "TESTING": "true",
    "DATABASE_URL": TEST_DATABASE_URL,
    "REDIS_URL": TEST_REDIS_URL,
    "JWT_SECRET_KEY": "test_secret_key_for_testing_only",
    "LOG_LEVEL": "WARNING",  # Снижаем уровень логирования для тестов
})
