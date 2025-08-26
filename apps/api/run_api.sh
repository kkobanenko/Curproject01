#!/bin/bash

# Скрипт запуска FastAPI сервера RAG Platform

echo "🚀 Запуск FastAPI сервера RAG Platform..."

# Установка переменных окружения
export SECRET_KEY="your-super-secret-key-for-development-only"
export REDIS_URL="redis://localhost:6379/1"
export PG_DSN="postgresql://postgres:postgres@localhost:5432/rag_app"

# Запуск сервера
echo "📍 Сервер будет доступен по адресу: http://localhost:8080"
echo "📊 Документация API: http://localhost:8080/docs"
echo "🔍 Альтернативная документация: http://localhost:8080/redoc"

# Запуск с uvicorn
uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --reload \
    --log-level info

