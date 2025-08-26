"""
FastAPI приложение для RAG Platform
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from .routers import search, documents, answers, feedback, webhooks, auth
from .settings import get_settings
from .services.health_check import HealthChecker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные
settings = get_settings()
health_checker = HealthChecker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запуск
    logger.info("🚀 Запуск RAG Platform API...")
    
    # Проверка здоровья системы
    try:
        health_status = await health_checker.check_all()
        if health_status['overall_status'] == 'healthy':
            logger.info("✅ Система здорова, API готов к работе")
        else:
            logger.warning(f"⚠️ Система имеет проблемы: {health_status['issues']}")
    except Exception as e:
        logger.error(f"❌ Ошибка проверки здоровья системы: {e}")
    
    yield
    
    # Завершение
    logger.info("🛑 Завершение работы RAG Platform API")

# Создание FastAPI приложения
app = FastAPI(
    title="RAG Platform API",
    description="API для локальной RAG системы с поддержкой поиска, ответов и управления документами",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов"""
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(f"📥 {request.method} {request.url.path} - {request.client.host if request.client else 'unknown'}")
    
    # Обрабатываем запрос
    response = await call_next(request)
    
    # Логируем результат
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    # Добавляем заголовок времени обработки
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Middleware для обработки ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"❌ Необработанная ошибка: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Произошла внутренняя ошибка сервера",
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    logger.warning(f"⚠️ HTTP ошибка {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )

# Подключение роутеров
app.include_router(
    search.router,
    prefix="/api/v1/search",
    tags=["search"]
)

app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["documents"]
)

app.include_router(
    answers.router,
    prefix="/api/v1/answers",
    tags=["answers"]
)

app.include_router(
    feedback.router,
    prefix="/api/v1/feedback",
    tags=["feedback"]
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"]
)

app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["auth"]
)

# Основные эндпоинты
@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "RAG Platform API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled in production"
    }

@app.get("/health")
async def health():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def health_detailed():
    """Детальная проверка здоровья системы"""
    try:
        health_status = await health_checker.check_all()
        return health_status
    except Exception as e:
        logger.error(f"Ошибка детальной проверки здоровья: {e}")
        return {
            "overall_status": "error",
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/info")
async def info():
    """Информация о системе"""
    return {
        "name": "RAG Platform API",
        "version": "1.0.0",
        "description": "API для локальной RAG системы",
        "features": [
            "Семантический поиск по документам",
            "Генерация ответов с цитированием",
            "Управление документами",
            "Сбор обратной связи",
            "Webhook интеграции"
        ],
        "config": {
            "debug": settings.debug,
            "max_file_size": settings.max_file_size_mb,
            "supported_formats": settings.supported_mime_types,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap
        }
    }

# Обработчик для несуществующих маршрутов
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Обработчик для несуществующих маршрутов"""
    raise HTTPException(
        status_code=404,
        detail=f"Маршрут '/{full_path}' не найден. Используйте /docs для просмотра доступных эндпоинтов."
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
