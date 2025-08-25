#!/bin/bash

# Скрипт инициализации Apache Airflow для RAG Platform
# Запускать внутри контейнера Airflow

set -e

echo "🚀 Инициализация Apache Airflow для RAG Platform..."

# Проверяем переменные окружения
if [ -z "$AIRFLOW_HOME" ]; then
    export AIRFLOW_HOME=/opt/airflow
fi

if [ -z "$AIRFLOW__CORE__SQL_ALCHEMY_CONN" ]; then
    export AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://postgres:postgres@postgres:5432/airflow"
fi

if [ -z "$AIRFLOW__CELERY__BROKER_URL" ]; then
    export AIRFLOW__CELERY__BROKER_URL="redis://redis:6379/0"
fi

echo "📁 AIRFLOW_HOME: $AIRFLOW_HOME"
echo "🗄️  Database: $AIRFLOW__CORE__SQL_ALCHEMY_CONN"
echo "📨 Broker: $AIRFLOW__CELERY__BROKER_URL"

# Создаем необходимые директории
echo "📂 Создание директорий..."
mkdir -p $AIRFLOW_HOME/dags
mkdir -p $AIRFLOW_HOME/logs
mkdir -p $AIRFLOW_HOME/plugins
mkdir -p $AIRFLOW_HOME/temp
mkdir -p $AIRFLOW_HOME/config

# Копируем конфигурацию
if [ -f "$AIRFLOW_HOME/airflow.cfg" ]; then
    echo "⚙️  Копирование конфигурации..."
    cp $AIRFLOW_HOME/airflow.cfg $AIRFLOW_HOME/config/airflow.cfg
fi

# Инициализация базы данных
echo "🗄️  Инициализация базы данных..."
airflow db init

# Создание пользователя администратора
echo "👤 Создание администратора..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@rag-platform.local \
    --password admin

# Создание подключений
echo "🔗 Создание подключений..."

# PostgreSQL для RAG
airflow connections add 'rag_postgres' \
    --conn-type 'postgres' \
    --conn-host 'postgres' \
    --conn-login 'postgres' \
    --conn-password 'postgres' \
    --conn-schema 'rag_app' \
    --conn-port '5432'

# ClickHouse для метрик
airflow connections add 'clickhouse_metrics' \
    --conn-type 'http' \
    --conn-host 'clickhouse' \
    --conn-port '8123' \
    --conn-login '' \
    --conn-password ''

# Redis для Celery
airflow connections add 'redis_celery' \
    --conn-type 'redis' \
    --conn-host 'redis' \
    --conn-port '6379' \
    --conn-login '' \
    --conn-password ''

# Создание переменных
echo "📊 Создание переменных..."

# PostgreSQL DSN
airflow variables set 'pg_dsn' 'postgresql://postgres:postgres@postgres:5432/rag_app'

# ClickHouse
airflow variables set 'clickhouse_url' 'http://clickhouse:8123'
airflow variables set 'clickhouse_db' 'rag'

# RAG Platform
airflow variables set 'rag_core_path' '/opt/airflow/rag_core'
airflow variables set 'inbox_path' '/opt/airflow/inbox'
airflow variables set 'processed_path' '/opt/airflow/processed'

# Системные настройки
airflow variables set 'max_document_size_mb' '100'
airflow variables set 'supported_mime_types' '["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/html", "message/rfc822"]'
airflow variables set 'chunk_size' '1000'
airflow variables set 'chunk_overlap' '200'

# Создание пулов
echo "🏊 Создание пулов ресурсов..."

# Пул для обработки документов
airflow pools set 'document_processing' 4 'Пул для обработки документов'

# Пул для OCR
airflow pools set 'ocr_processing' 2 'Пул для OCR обработки'

# Пул для индексации
airflow pools set 'indexing' 3 'Пул для индексации в векторное хранилище'

# Пул для метрик
airflow pools set 'metrics_collection' 2 'Пул для сбора метрик'

# Синхронизация DAG
echo "🔄 Синхронизация DAG..."
airflow dags reserialize

# Проверка DAG
echo "✅ Проверка DAG..."
airflow dags list

# Проверка подключений
echo "🔗 Проверка подключений..."
airflow connections list

# Проверка переменных
echo "📊 Проверка переменных..."
airflow variables list

# Проверка пулов
echo "🏊 Проверка пулов..."
airflow pools list

echo "🎉 Инициализация Airflow завершена успешно!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Запустите веб-сервер: airflow webserver"
echo "2. Запустите планировщик: airflow scheduler"
echo "3. Откройте веб-интерфейс: http://localhost:8080"
echo "4. Войдите с учетными данными: admin/admin"
echo ""
echo "🔧 Полезные команды:"
echo "- Просмотр DAG: airflow dags list"
echo "- Тест DAG: airflow dags test <dag_id>"
echo "- Запуск DAG: airflow dags trigger <dag_id>"
echo "- Логи: airflow tasks logs <dag_id> <task_id>"
echo ""
echo "📚 Документация:"
echo "- Airflow: https://airflow.apache.org/docs/"
echo "- RAG Platform: /opt/airflow/README.md"
