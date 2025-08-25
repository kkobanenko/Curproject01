"""
FastAPI сервис для RAG-платформы
Основные эндпоинты: поиск, ответы, загрузка документов
"""

import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routers import search_router, documents_router, chat_router
from .services.rag_pipeline import RAGPipeline
from .services.embeddings import EmbeddingService
from .services.vectorstore import VectorStoreService
from .schemas.common import HealthResponse, ErrorResponse
from .settings import get_settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="RAG Platform API",
    description="API для RAG-платформы с семантическим поиском и генерацией ответов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting RAG Platform API...")
    
    try:
        # Проверяем настройки
        settings = get_settings()
        logger.info(f"API configured for environment: {settings.app_env}")
        
        # Инициализируем сервисы
        await _initialize_services()
        
        logger.info("RAG Platform API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down RAG Platform API...")

async def _initialize_services():
    """Инициализация основных сервисов"""
    try:
        # Проверяем доступность Ollama
        embedding_service = EmbeddingService()
        if await embedding_service.is_available():
            logger.info("Embedding service (Ollama) is available")
        else:
            logger.warning("Embedding service (Ollama) is not available")
        
        # Проверяем подключение к векторному хранилищу
        vector_store = VectorStoreService()
        if await vector_store.is_available():
            logger.info("Vector store (PostgreSQL + pgvector) is available")
        else:
            logger.warning("Vector store (PostgreSQL + pgvector) is not available")
        
        # Инициализируем RAG пайплайн
        rag_pipeline = RAGPipeline()
        logger.info("RAG pipeline initialized")
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        # Не прерываем запуск, но логируем ошибку

@app.get("/", response_model=HealthResponse)
async def root():
    """Корневой эндпоинт"""
    return HealthResponse(
        status="healthy",
        message="RAG Platform API is running",
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем основные компоненты
        checks = {}
        
        # Проверка Ollama
        embedding_service = EmbeddingService()
        checks["ollama"] = await embedding_service.is_available()
        
        # Проверка PostgreSQL
        vector_store = VectorStoreService()
        checks["postgresql"] = await vector_store.is_available()
        
        # Общий статус
        overall_status = all(checks.values())
        
        return HealthResponse(
            status="healthy" if overall_status else "degraded",
            message="Service health check completed",
            version="1.0.0",
            details=checks
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            version="1.0.0"
        )

@app.get("/api/v1/models", tags=["models"])
async def list_models():
    """Список доступных моделей"""
    try:
        embedding_service = EmbeddingService()
        models = await embedding_service.list_models()
        
        return {
            "models": models,
            "default_embedding": "bge-m3",
            "default_llm": "llama3:8b"
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/stats", tags=["statistics"])
async def get_statistics():
    """Статистика платформы"""
    try:
        vector_store = VectorStoreService()
        stats = await vector_store.get_statistics()
        
        return {
            "vector_store": stats,
            "platform": {
                "version": "1.0.0",
                "status": "running"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            message="An unexpected error occurred",
            details=str(exc)
        ).dict()
    )

if __name__ == "__main__":
    # Запуск для разработки
    port = int(os.getenv("API_PORT", 8080))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
