#!/bin/bash

# RAG Platform - Скрипт инициализации проекта

set -e

echo "🚀 Инициализация RAG Platform..."

# Проверка зависимостей
echo "📋 Проверка зависимостей..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и Docker Compose."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose."
    exit 1
fi

echo "✅ Docker и Docker Compose доступны"

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p data/inbox
mkdir -p uploads
mkdir -p backups
mkdir -p logs

# Копирование конфигурации
echo "📝 Настройка конфигурации..."

if [ ! -f "infra/compose/.env.local" ]; then
    cp infra/compose/env.example infra/compose/.env.local
    echo "⚠️  Создан файл .env.local. Отредактируйте его перед запуском!"
    echo "   Особое внимание уделите паролям и настройкам Ollama."
else
    echo "✅ Файл .env.local уже существует"
fi

# Проверка Ollama
echo "🤖 Проверка Ollama..."

if ! docker ps | grep -q ollama; then
    echo "ℹ️  Ollama не запущен. Запустите его для загрузки моделей:"
    echo "   docker run -d --name ollama -p 11434:11434 ollama/ollama"
    echo "   docker exec -it ollama ollama pull llama3:8b"
    echo "   docker exec -it ollama ollama pull bge-m3"
else
    echo "✅ Ollama запущен"
fi

# Создание .gitignore
echo "🔒 Настройка .gitignore..."

if [ ! -f ".gitignore" ]; then
    cat > .gitignore << EOF
# Данные
data/
uploads/
backups/
logs/

# Конфигурация
.env
.env.local
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore

# Airflow
airflow.cfg
airflow.db
airflow-webserver.pid
webserver_config.py

# Superset
superset.db
superset_config.py
EOF
    echo "✅ Создан .gitignore"
else
    echo "✅ .gitignore уже существует"
fi

# Проверка Docker Compose
echo "🐳 Проверка Docker Compose конфигурации..."

if [ -f "infra/compose/docker-compose.yml" ]; then
    echo "✅ Docker Compose файл найден"
else
    echo "❌ Docker Compose файл не найден"
    exit 1
fi

# Создание Makefile если не существует
if [ ! -f "Makefile" ]; then
    echo "📋 Makefile не найден, создаю базовый..."
    cat > Makefile << 'EOF'
# RAG Platform Makefile

.PHONY: help build up down logs clean

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать образы
	docker-compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env.local build

up: ## Запустить сервисы
	docker-compose -f infra/compose/docker-compose.yml --env-file infra/compose/.env.local up -d

down: ## Остановить сервисы
	docker-compose -f infra/compose/docker-compose.yml down

logs: ## Показать логи
	docker-compose -f infra/compose/docker-compose.yml logs -f

clean: ## Очистить все
	docker-compose -f infra/compose/docker-compose.yml down -v --rmi all
EOF
    echo "✅ Создан базовый Makefile"
fi

echo ""
echo "🎉 Инициализация завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте infra/compose/.env.local"
echo "2. Запустите: make build && make up"
echo "3. Откройте http://localhost:8502"
echo ""
echo "📚 Документация: README.md"
echo "🔧 Команды: make help"
