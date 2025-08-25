# Airflow Pipelines для RAG Platform

Этот каталог содержит Apache Airflow DAG для автоматизации процессов RAG системы.

## Обзор

Airflow пайплайны обеспечивают:
- **Автоматическую загрузку документов** из inbox директории
- **Обработку и индексацию** документов в векторное хранилище
- **Синхронизацию метрик** в ClickHouse для мониторинга
- **Техническое обслуживание** системы (очистка, оптимизация)

## Структура DAG

### 1. ingest_documents_dag.py
**Назначение**: Автоматическое обнаружение и валидация новых документов

**Расписание**: Каждые 15 минут (`*/15 * * * *`)

**Задачи**:
- `discover_new_documents` - Поиск новых файлов в inbox
- `validate_documents` - Проверка файлов (размер, формат, читаемость)
- `initiate_processing` - Запуск процесса обработки
- `update_status` - Обновление статуса документов
- `cleanup_temp_files` - Очистка временных файлов
- `generate_report` - Формирование отчета

**Особенности**:
- SHA256 хеширование для дедупликации
- Валидация MIME типов
- Проверка размера файлов
- Интеграция с RAG Core

### 2. process_and_index_dag.py
**Назначение**: Детальная обработка и индексация документов

**Расписание**: Каждый час (`0 * * * *`)

**Задачи**:
- `get_pending_documents` - Получение документов для обработки
- `parse_documents` - Парсинг документов (PDF, DOCX, XLSX, HTML, EML)
- `extract_tables` - Извлечение таблиц из документов
- `create_chunks` - Создание чанков для индексации
- `generate_embeddings` - Генерация векторных представлений
- `index_to_vectorstore` - Индексация в PostgreSQL с pgvector
- `update_processing_status` - Обновление статуса обработки
- `generate_processing_report` - Формирование отчета

**Особенности**:
- Поддержка множественных форматов документов
- OCR обработка для изображений
- Извлечение таблиц с помощью Camelot, Tabula, PaddleOCR
- Векторная индексация с HNSW

### 3. sync_clickhouse_metrics_dag.py
**Назначение**: Синхронизация метрик RAG системы в ClickHouse

**Расписание**: Каждые 2 часа (`0 */2 * * *`)

**Задачи**:
- `collect_rag_metrics` - Сбор метрик RAG системы
- `collect_search_metrics` - Сбор метрик поиска
- `collect_quality_metrics` - Сбор метрик качества
- `transform_metrics_for_clickhouse` - Трансформация метрик
- `send_metrics_to_clickhouse` - Отправка в ClickHouse
- `generate_metrics_report` - Формирование отчета

**Собираемые метрики**:
- Количество документов, чанков, эмбеддингов
- Статистика поиска и использования
- Метрики качества ответов
- Системные метрики (диск, память, uptime)

### 4. system_maintenance_dag.py
**Назначение**: Мониторинг и техническое обслуживание системы

**Расписание**: Каждый день в 2:00 (`0 2 * * *`)

**Задачи**:
- `check_system_health` - Проверка состояния системы
- `cleanup_old_logs` - Очистка старых логов
- `optimize_database` - Оптимизация базы данных
- `generate_maintenance_report` - Формирование отчета

**Проверки здоровья системы**:
- Использование дискового пространства
- Использование памяти
- Подключения к базе данных
- Состояние RAG Core
- Временные файлы

## Конфигурация

### Переменные окружения
```bash
# PostgreSQL
PG_DSN=postgresql://postgres:postgres@postgres:5432/rag_app

# ClickHouse
CLICKHOUSE_URL=http://clickhouse:8123
CLICKHOUSE_DB=rag

# Inbox директория
INBOX_HOSTDIR=../../data/inbox
```

### Airflow Variables
```python
# В Airflow UI или через CLI
airflow variables set pg_dsn "postgresql://postgres:postgres@postgres:5432/rag_app"
airflow variables set clickhouse_url "http://clickhouse:8123"
airflow variables set clickhouse_db "rag"
```

## Зависимости

### Python пакеты
```txt
# requirements.txt
apache-airflow>=2.7.0
psycopg2-binary>=2.9.0
psutil>=5.9.0
```

### Системные зависимости
```dockerfile
# Dockerfile
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

## Развертывание

### 1. Подготовка окружения
```bash
# Клонирование репозитория
git clone <repository>
cd Curproject01

# Создание необходимых директорий
mkdir -p data/inbox
mkdir -p data/processed
mkdir -p data/logs
```

### 2. Запуск через Docker Compose
```bash
# Запуск инфраструктуры
cd infra/compose
docker-compose up -d postgres redis

# Запуск Airflow
docker-compose up -d airflow-webserver airflow-scheduler

# Проверка статуса
docker-compose ps
```

### 3. Инициализация Airflow
```bash
# Создание пользователя
docker-compose exec airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Синхронизация DAG
docker-compose exec airflow-scheduler airflow dags reserialize
```

## Мониторинг

### Airflow UI
- **URL**: http://localhost:8080
- **Логин**: admin/admin
- **DAG**: ingest_documents, process_and_index_documents, sync_clickhouse_metrics, system_maintenance

### Логи
```bash
# Логи планировщика
docker-compose logs airflow-scheduler

# Логи веб-сервера
docker-compose logs airflow-webserver

# Логи конкретного DAG
docker-compose exec airflow-webserver airflow tasks logs <dag_id> <task_id>
```

### Метрики
- **ClickHouse**: http://localhost:8123
- **Superset**: http://localhost:8088 (если настроен)

## Устранение неполадок

### Частые проблемы

#### 1. DAG не запускается
```bash
# Проверка синхронизации
docker-compose exec airflow-scheduler airflow dags reserialize

# Проверка прав доступа
docker-compose exec airflow-webserver ls -la /opt/airflow/dags/
```

#### 2. Ошибки подключения к БД
```bash
# Проверка доступности PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Проверка переменных окружения
docker-compose exec airflow-webserver airflow variables list
```

#### 3. Ошибки RAG Core
```bash
# Проверка доступности модулей
docker-compose exec airflow-webserver python -c "import sys; sys.path.append('/opt/airflow/rag_core'); from rag_core.rag_pipeline import RAGPipeline"

# Проверка зависимостей
docker-compose exec airflow-webserver pip list | grep rag
```

### Логирование
```python
# В DAG функциях
import logging
logger = logging.getLogger(__name__)

logger.info("Task started")
logger.warning("Warning message")
logger.error("Error message")
```

## Разработка

### Добавление нового DAG
1. Создайте файл в `dags/` директории
2. Определите DAG с уникальным `dag_id`
3. Добавьте теги для категоризации
4. Настройте расписание (`schedule_interval`)
5. Добавьте тесты в `test_*.py`

### Структура DAG
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

# Параметры DAG
default_args = {
    'owner': 'rag-platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Создание DAG
dag = DAG(
    'example_dag',
    default_args=default_args,
    description='Описание DAG',
    schedule_interval='0 * * * *',
    max_active_runs=1,
    tags=['rag', 'example']
)

# Определение задач
start_task = EmptyOperator(task_id='start', dag=dag)
process_task = PythonOperator(
    task_id='process_data',
    python_callable=process_function,
    dag=dag
)
end_task = EmptyOperator(task_id='end', dag=dag)

# Зависимости
start_task >> process_task >> end_task
```

### Тестирование
```bash
# Запуск тестов
cd pipelines/airflow
python test_new_dags.py

# Проверка синтаксиса DAG
docker-compose exec airflow-webserver python -m py_compile dags/*.py
```

## Производительность

### Оптимизация
- **Параллелизм**: Настройте `max_active_runs` и `concurrency`
- **Ресурсы**: Используйте `pool` для ограничения ресурсов
- **Кэширование**: Включите XCom backend для Redis
- **Мониторинг**: Отслеживайте время выполнения задач

### Масштабирование
- **Worker процессы**: Настройте количество worker'ов
- **База данных**: Используйте внешнюю PostgreSQL для метаданных
- **Очереди**: Настройте Celery для распределения задач

## Безопасность

### Аутентификация
- Используйте LDAP или OAuth для корпоративных сред
- Настройте роли и разрешения
- Регулярно обновляйте пароли

### Сетевая безопасность
- Ограничьте доступ к Airflow UI
- Используйте HTTPS для веб-интерфейса
- Настройте firewall правила

### Данные
- Шифруйте чувствительные данные
- Используйте переменные окружения для секретов
- Регулярно делайте резервные копии метаданных

## Поддержка

### Документация
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [RAG Core Documentation](../packages/rag_core/README.md)
- [Project README](../../README.md)

### Логи и отладка
- Проверяйте логи Airflow для диагностики
- Используйте XCom для передачи данных между задачами
- Мониторьте метрики производительности

### Обновления
- Регулярно обновляйте Airflow до последней стабильной версии
- Тестируйте DAG в staging окружении
- Используйте версионирование для DAG
