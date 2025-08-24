# RAG Platform

CPU-only локальная RAG-платформа с Streamlit UI и FastAPI backend.

## 🚀 Возможности

- **Загрузка документов** - PDF, DOCX, XLSX, HTML, изображения
- **OCR и извлечение таблиц** - автоматическое распознавание с поддержкой русского и английского языков
- **Семантический поиск** - поиск по смыслу через векторные эмбеддинги
- **RAG чат** - ответы на вопросы с цитатами из документов
- **Локальные LLM** - через Ollama (llama3:8b, llama3.1:8b)
- **Векторное хранилище** - PostgreSQL + pgvector с HNSW индексами
- **Автоматизация** - Airflow для обработки документов
- **Дашборды** - Apache Superset для метрик и аналитики

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   FastAPI       │    │   Airflow       │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (Pipelines)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │   ClickHouse    │
                       │   + pgvector    │    │   (Metrics)     │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Ollama      │
                       │  (LLM + Embed)  │
                       └─────────────────┘
```

## 📋 Требования

- Ubuntu 22.04+
- Docker Engine + Docker Compose v2
- Python 3.11+
- Git

## 🚀 Быстрый старт

1. **Клонирование репозитория**
   ```bash
   git clone <repository-url>
   cd rag-platform
   ```

2. **Настройка переменных окружения**
   ```bash
   cp infra/compose/env.example infra/compose/.env
   # Отредактируйте .env файл с вашими настройками
   ```

3. **Запуск сервисов**
   ```bash
   make build    # Сборка Docker образов
   make up       # Запуск всех сервисов
   ```

4. **Доступ к приложениям**
   - Streamlit UI: http://localhost:8501
   - FastAPI: http://localhost:8081
   - Airflow: http://localhost:8080
   - Superset: http://localhost:8088
   - ClickHouse: http://localhost:8123

## 📁 Структура проекта

```
rag-platform/
├── apps/                    # Приложения
│   ├── streamlit_app/      # Streamlit UI
│   └── api/                # FastAPI backend
├── packages/                # Переиспользуемые пакеты
│   └── rag_core/           # Основная RAG логика
├── pipelines/               # Airflow пайплайны
│   └── airflow/
├── infra/                   # Инфраструктура
│   ├── compose/            # Docker Compose
│   ├── db/                 # Базы данных
│   └── superset/           # Дашборды
├── configs/                 # Конфигурации
├── data/                    # Данные
│   └── inbox/              # Входящие документы
└── tests/                   # Тесты
```

## 🔧 Конфигурация

### Переменные окружения

Основные настройки в `infra/compose/.env`:

- `POSTGRES_USER/PASSWORD` - PostgreSQL
- `AIRFLOW_USER/PASSWORD` - Airflow
- `OLLAMA_LLM_MODEL` - модель LLM (по умолчанию llama3:8b)
- `OLLAMA_EMBED_MODEL` - модель эмбеддингов (по умолчанию bge-m3)

### Модели Ollama

```bash
# Загрузка моделей
ollama pull llama3:8b
ollama pull bge-m3
```

## 📊 Использование

### Загрузка документов

1. Поместите документы в папку `data/inbox/`
2. Airflow автоматически обнаружит и обработает их
3. Документы будут разбиты на чанки и векторизованы

### Поиск

- **Семантический поиск** через Streamlit UI
- **API поиска** через FastAPI endpoints
- **RAG чат** для вопросов с контекстом

### Мониторинг

- **Airflow** - статус пайплайнов
- **Superset** - дашборды метрик
- **ClickHouse** - аналитика и логи

## 🛠️ Разработка

### Установка зависимостей

```bash
make install      # Основные зависимости
make dev          # + dev зависимости
```

### Линтинг и форматирование

```bash
make lint         # Проверка кода
make format       # Форматирование
```

### Тесты

```bash
make test         # Запуск тестов
```

## 🔒 Безопасность

- ACL/роли/тенанты в PostgreSQL
- Фильтрация ретрива по правам доступа
- Переменные окружения для секретов
- CORS настройки для API

## 📈 Производительность

- **Векторный поиск**: HNSW индексы в pgvector
- **Размер эмбеддингов**: 384-768 (оптимизировано для CPU)
- **Кэширование**: Redis для частых запросов
- **OLAP**: ClickHouse для метрик и аналитики

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License

## 🆘 Поддержка

- Issues: GitHub Issues
- Документация: README и inline комментарии
- Примеры: папка `examples/`

## 🔮 Roadmap

- [ ] Reranker для улучшения точности поиска
- [ ] Поддержка большего количества форматов документов
- [ ] Веб-хуки для интеграций
- [ ] Расширенные метрики качества
- [ ] Multi-tenant изоляция
- [ ] Backup и восстановление
