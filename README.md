# 🔍 RAG Platform

Платформа для семантического поиска и анализа документов с использованием RAG (Retrieval-Augmented Generation).

## 🚀 Возможности

- **Семантический поиск** по документам с использованием векторных эмбеддингов
- **RAG чат** с контекстом из загруженных документов
- **Поддержка множества форматов**: PDF, DOCX, XLSX, HTML, TXT, изображения
- **OCR обработка** для сканированных документов
- **Извлечение таблиц** с сохранением структуры
- **Локальные LLM** через Ollama (без отправки данных в интернет)
- **Векторное хранилище** PostgreSQL + pgvector
- **Веб-интерфейс** Streamlit для удобной работы

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   Airflow       │
│   (Frontend)    │◄──►│   (API)         │◄──►│   (Pipelines)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │   ClickHouse    │
                       │   + pgvector    │    │   (Analytics)   │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Ollama      │
                       │   (LLM/Embed)  │
                       └─────────────────┘
```

## 📋 Требования

- **Docker** и **Docker Compose**
- **Git**
- **Python 3.11+** (для локальной разработки)
- **4GB+ RAM** (для работы Ollama)

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <your-repo-url>
cd Curproject01
```

### 2. Инициализация проекта

```bash
make init
```

Это создаст необходимые директории и скопирует пример конфигурации.

### 3. Настройка окружения

Отредактируйте файл `infra/compose/.env.local`:

```bash
# Основные настройки
PROJECT_NAME=rag-platform
TZ=Europe/Moscow

# База данных
POSTGRES_PASSWORD=your_secure_password
AIRFLOW_PASSWORD=your_airflow_password

# Ollama модели
OLLAMA_LLM_MODEL=llama3:8b
OLLAMA_EMBED_MODEL=bge-m3
```

### 4. Запуск сервисов

#### Вариант A: Полный запуск (Docker)
```bash
# Сборка и запуск всех сервисов
make build
make up

# Или пошагово:
make build-api
make build-streamlit
make build-airflow
make up
```

#### Вариант B: Режим разработки (локально)
```bash
# Запуск только базы данных и Ollama
make dev

# Приложения запустятся автоматически:
# - API: http://localhost:8081
# - Streamlit: http://localhost:8501
```

### 5. Доступ к сервисам

- **Streamlit UI**: http://localhost:8501
- **API Docs**: http://localhost:8081/docs
- **Airflow**: http://localhost:8080 (admin/airflow123)
- **Superset**: http://localhost:8088

### 6. Проверка работоспособности

```bash
# Проверка здоровья системы
make health

# Демонстрация функциональности
make demo

# Запуск тестов
make test
```

## 🛠️ Режим разработки

Для локальной разработки без Docker:

```bash
# Запуск только базы данных и Ollama
make dev

# В отдельном терминале - API
cd apps/api
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8081

# В отдельном терминале - Streamlit
cd apps/streamlit_app
pip install -r requirements.txt
streamlit run src/main.py --server.port 8501
```

## 📚 Использование

### Загрузка документов

1. Откройте Streamlit UI
2. Перейдите в раздел "Загрузка"
3. Выберите файл и нажмите "Загрузить"
4. Документ автоматически обработается через Airflow

### Поиск по документам

1. В разделе "Поиск" введите запрос
2. Выберите количество результатов
3. Просматривайте найденные фрагменты с оценкой релевантности

### Чат с документами

1. В разделе "Чат" задайте вопрос
2. Система найдет релевантные документы
3. LLM сгенерирует ответ на основе найденного контекста

## 🎯 Примеры использования

### API запросы

```bash
# Поиск документов
curl -X POST "http://localhost:8081/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "RAG платформа", "top_k": 5}'

# Чат с документами
curl -X POST "http://localhost:8081/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Что такое RAG?", "top_k": 3}'

# Загрузка документа
curl -X POST "http://localhost:8081/api/v1/upload" \
  -F "file=@document.pdf" \
  -F "title=Мой документ"
```

### Программное использование

```python
import requests

# Поиск
response = requests.post("http://localhost:8081/api/v1/search", 
    json={"query": "семантический поиск", "top_k": 10})
results = response.json()

# Чат
response = requests.post("http://localhost:8081/api/v1/chat",
    json={"message": "Объясни RAG", "use_context": True})
answer = response.json()
```

## 🔧 Команды Make

```bash
make help          # Показать все команды
make up            # Запустить сервисы
make down          # Остановить сервисы
make logs          # Показать логи
make build         # Собрать образы
make clean         # Очистить все
make status        # Статус сервисов
make backup        # Создать бэкап БД

# Разработка
make dev           # Запуск в режиме разработки
make dev-stop      # Остановка в режиме разработки

# Тестирование
make test          # Запуск всех тестов
make test-api      # Тесты API
make test-streamlit # Тесты Streamlit

# Утилиты
make health        # Проверка здоровья системы
make demo          # Демонстрация функциональности
```

## 📁 Структура проекта

```
Curproject01/
├── apps/                          # Приложения
│   ├── api/                       # FastAPI сервис
│   │   ├── src/
│   │   │   ├── routers/           # API роутеры
│   │   │   ├── services/          # Бизнес-логика
│   │   │   ├── schemas/           # Pydantic схемы
│   │   │   └── settings/          # Конфигурация
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── streamlit_app/             # Веб-интерфейс
│       ├── src/
│       ├── Dockerfile
│       └── requirements.txt
├── packages/                       # Переиспользуемые пакеты
│   └── rag_core/                  # Основная логика RAG
├── pipelines/                      # Airflow пайплайны
│   └── airflow/
├── infra/                         # Инфраструктура
│   ├── compose/                   # Docker Compose
│   ├── db/                        # Скрипты БД
│   └── superset/                  # Конфигурация Superset
├── configs/                       # Конфигурации
├── data/                          # Данные (создается автоматически)
│   └── inbox/                     # Входящие документы
└── Makefile                       # Команды управления
```

## 🔒 Безопасность

- Все данные остаются в локальной сети
- LLM и эмбеддинги работают локально через Ollama
- Поддержка ACL и тенантов для разграничения доступа
- Переменные окружения для конфиденциальных данных

## ⚡ Производительность и оптимизация

### Настройки векторного поиска

```toml
# configs/app.toml
[vectorstore]
hnsw_m = 16                    # Количество соседей в HNSW
hnsw_ef_construction = 64      # Точность построения индекса
hnsw_ef_search = 40           # Точность поиска
```

### Оптимизация эмбеддингов

- **Размер**: 1024 измерения (оптимизировано для CPU)
- **Модель**: BGE-M3 (мультиязычная, высокая точность)
- **Кэширование**: Redis для частых запросов
- **Батчинг**: Группировка запросов для эффективности

### Настройки RAG

```toml
[rag]
chunk_size = 1000              # Размер чанка
chunk_overlap = 200            # Перекрытие чанков
default_top_k = 20             # Количество результатов поиска
rerank_top_k = 3               # Количество для переранжирования
```

### Мониторинг производительности

```bash
# Время ответа API
curl -w "@-" -o /dev/null -s "http://localhost:8081/health"

# Статистика базы данных
docker exec rag-platform-postgres psql -U postgres -d rag_app -c "SELECT * FROM pg_stat_user_tables;"

# Использование памяти
docker stats rag-platform-ollama
```

## 🧪 Тестирование

```bash
# Запуск тестов API
make test-api

# Линтинг кода
make lint

# Форматирование кода
make format
```

## 📊 Мониторинг и логирование

### Статус системы

```bash
# Общий статус
make status

# Проверка здоровья
make health

# Мониторинг ресурсов
make monitor
```

### Логи

```bash
# Логи всех сервисов
make logs

# Логи конкретного сервиса
make logs-api
make logs-streamlit
make logs-airflow

# Логи в реальном времени
docker-compose -f infra/compose/docker-compose.yml logs -f [service_name]
```

### Дашборды

- **Superset**: http://localhost:8088 - аналитика и метрики
- **Airflow**: http://localhost:8080 - мониторинг пайплайнов
- **ClickHouse**: http://localhost:8123 - аналитика данных

### Метрики

```bash
# Статистика API
curl http://localhost:8081/api/v1/stats

# Статистика базы данных
curl http://localhost:8081/health

# Модели Ollama
curl http://localhost:11434/api/tags
```

## 🚨 Устранение неполадок

### API недоступен

```bash
# Проверить статус
make status

# Посмотреть логи
make logs-api

# Перезапустить
make restart

# Или в режиме разработки
make dev-stop
make dev
```

### Ollama не отвечает

```bash
# Проверить контейнер
docker ps | grep ollama

# Логи Ollama
docker logs rag-platform-ollama

# Перезапустить
docker restart rag-platform-ollama

# Проверить модели
curl http://localhost:11434/api/tags
```

### Проблемы с базой данных

```bash
# Проверить подключение
make shell-api
python -c "from src.services.vectorstore import VectorStoreService; import asyncio; print(asyncio.run(VectorStoreService().is_available()))"

# Создать бэкап перед сбросом
make backup

# Проверить логи PostgreSQL
docker logs rag-platform-postgres
```

### Проблемы с зависимостями

```bash
# Переустановить зависимости
cd apps/api && pip install -r requirements.txt --force-reinstall
cd ../streamlit_app && pip install -r requirements.txt --force-reinstall

# Проверить версии Python
python3 --version
pip3 --version
```

### Проблемы с портами

```bash
# Проверить занятые порты
netstat -tuln | grep -E ':(8081|8501|5432|6379|8123|11434)'

# Остановить процессы на портах
sudo lsof -ti:8081 | xargs kill -9
sudo lsof -ti:8501 | xargs kill -9
```

### Общие проблемы

```bash
# Полная проверка системы
make health

# Очистка и перезапуск
make clean
make init
make build
make up

# В режиме разработки
make dev-stop
make dev
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 🔮 Расширение функциональности

### Добавление новых форматов документов

```python
# apps/api/src/services/parsers/custom_parser.py
from .base_parser import BaseParser

class CustomParser(BaseParser):
    def parse(self, file_path: str) -> dict:
        # Ваша логика парсинга
        pass
```

### Интеграция новых LLM

```python
# apps/api/src/services/llm/custom_llm.py
from .base_llm import BaseLLM

class CustomLLM(BaseLLM):
    async def generate(self, prompt: str) -> str:
        # Ваша логика генерации
        pass
```

### Создание новых эндпоинтов

```python
# apps/api/src/routers/custom.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom")
async def custom_endpoint():
    return {"message": "Custom functionality"}
```

### Добавление новых метрик

```python
# apps/api/src/services/metrics.py
class MetricsService:
    async def track_custom_metric(self, name: str, value: float):
        # Отправка в ClickHouse
        pass
```

### Кастомизация UI

```python
# apps/streamlit_app/src/pages/custom_page.py
import streamlit as st

def show_custom_page():
    st.title("Custom Page")
    # Ваш UI код
```

## 📄 Лицензия

MIT License

## 🆘 Поддержка

- Создайте Issue для багов
- Обсуждения в Discussions
- Документация в Wiki

## 🗺️ Roadmap

### Версия 1.1 (Q1 2025)
- [ ] Reranker для улучшения точности поиска
- [ ] Поддержка большего количества форматов документов
- [ ] Веб-хуки для интеграций
- [ ] Расширенные метрики качества

### Версия 1.2 (Q2 2025)
- [ ] Multi-tenant изоляция
- [ ] Backup и восстановление
- [ ] API rate limiting
- [ ] Расширенная аналитика

### Версия 2.0 (Q3 2025)
- [ ] Микросервисная архитектура
- [ ] Kubernetes deployment
- [ ] Масштабируемость
- [ ] Enterprise features

---

**Примечание**: Это базовая версия платформы. Для продакшена рекомендуется:
- Настроить SSL/TLS
- Добавить аутентификацию
- Настроить мониторинг и алерты
- Регулярные бэкапы
- Логирование и аудит
