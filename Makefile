# RAG Platform Makefile

.PHONY: help build up down logs clean test lint format

# Переменные
COMPOSE_FILE = infra/compose/docker-compose.yml
ENV_FILE = infra/compose/.env.local

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker Compose команды
up: ## Запустить все сервисы
	@echo "🚀 Запуск RAG Platform..."
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d

down: ## Остановить все сервисы
	@echo "🛑 Остановка RAG Platform..."
	docker-compose -f $(COMPOSE_FILE) down

restart: ## Перезапустить сервисы
	@echo "🔄 Перезапуск сервисов..."
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) restart

logs: ## Показать логи
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api: ## Логи API
	docker-compose -f $(COMPOSE_FILE) logs -f api

logs-streamlit: ## Логи Streamlit
	docker-compose -f $(COMPOSE_FILE) logs -f streamlit

logs-airflow: ## Логи Airflow
	docker-compose -f $(COMPOSE_FILE) logs -f airflow-webserver

# Сборка образов
build: ## Собрать все образы
	@echo "🔨 Сборка образов..."
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build

build-api: ## Собрать образ API
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build api

build-streamlit: ## Собрать образ Streamlit
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build streamlit

build-airflow: ## Собрать образ Airflow
	docker-compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build airflow-webserver

# Разработка
dev: ## Запуск в режиме разработки
	@echo "🛠️ Запуск в режиме разработки..."
	./scripts/dev_start.sh

dev-stop: ## Остановка в режиме разработки
	@echo "🛑 Остановка в режиме разработки..."
	./scripts/dev_stop.sh

# Тестирование
test: ## Запустить тесты
	@echo "🧪 Запуск тестов..."
	./scripts/run_tests.sh

test-api: ## Тесты API
	cd apps/api && python3 test_basic.py

test-streamlit: ## Тесты Streamlit
	cd apps/streamlit_app && python3 test_basic.py

# Линтинг и форматирование
lint: ## Проверить код линтером
	@echo "🔍 Проверка кода..."
	cd apps/api && ruff check src/
	cd apps/streamlit_app && ruff check src/

format: ## Форматировать код
	@echo "✨ Форматирование кода..."
	cd apps/api && ruff format src/
	cd apps/streamlit_app && ruff format src/

# Очистка
clean: ## Очистить все контейнеры и образы
	@echo "🧹 Очистка..."
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all
	docker system prune -f

clean-volumes: ## Очистить тома
	@echo "🗑️ Очистка томов..."
	docker-compose -f $(COMPOSE_FILE) down -v

# Утилиты
status: ## Статус сервисов
	@echo "📊 Статус сервисов..."
	docker-compose -f $(COMPOSE_FILE) ps

health: ## Проверка здоровья системы
	@echo "🏥 Проверка здоровья системы..."
	./scripts/health_check.sh

demo: ## Демонстрация функциональности
	@echo "🎭 Демонстрация RAG Platform..."
	./scripts/demo.sh

shell-api: ## Shell в контейнер API
	docker-compose -f $(COMPOSE_FILE) exec api bash

shell-streamlit: ## Shell в контейнер Streamlit
	docker-compose -f $(COMPOSE_FILE) exec streamlit bash

shell-airflow: ## Shell в контейнер Airflow
	docker-compose -f $(COMPOSE_FILE) exec airflow-webserver bash

# Инициализация
init: ## Инициализация проекта
	@echo "🚀 Инициализация RAG Platform..."
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "📝 Создание .env.local..."; \
		cp infra/compose/env.example $(ENV_FILE); \
		echo "⚠️ Отредактируйте $(ENV_FILE) перед запуском"; \
	fi
	@echo "📁 Создание директорий..."
	mkdir -p data/inbox uploads
	@echo "✅ Инициализация завершена"

# Мониторинг
monitor: ## Мониторинг ресурсов
	@echo "📈 Мониторинг ресурсов..."
	docker stats --no-stream

# Бэкап
backup: ## Создать бэкап базы данных
	@echo "💾 Создание бэкапа..."
	mkdir -p backups
	docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U postgres rag_app > backups/rag_app_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Бэкап создан в backups/"

# Восстановление
restore: ## Восстановить базу данных из бэкапа
	@echo "📥 Восстановление базы данных..."
	@if [ -z "$(file)" ]; then \
		echo "❌ Укажите файл: make restore file=backups/filename.sql"; \
		exit 1; \
	fi
	docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U postgres rag_app < $(file)
	@echo "✅ База данных восстановлена"
