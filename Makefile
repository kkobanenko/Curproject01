.PHONY: help install dev test lint format clean build up down logs

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -e .

dev: ## Установить dev-зависимости
	pip install -e ".[dev]"

test: ## Запустить тесты
	pytest tests/ -v

lint: ## Проверить код линтерами
	ruff check .
	mypy .

format: ## Форматировать код
	black .
	ruff format .

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

build: ## Собрать Docker образы
	docker-compose -f infra/compose/docker-compose.yml build

up: ## Запустить все сервисы
	docker-compose -f infra/compose/docker-compose.yml up -d

down: ## Остановить все сервисы
	docker-compose -f infra/compose/docker-compose.yml down

logs: ## Показать логи
	docker-compose -f infra/compose/docker-compose.yml logs -f

setup: ## Первоначальная настройка
	cp infra/compose/.env.example infra/compose/.env
	@echo "Отредактируйте infra/compose/.env файл с вашими настройками"
	@echo "Затем запустите: make build && make up"
