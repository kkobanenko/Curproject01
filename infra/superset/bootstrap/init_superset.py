"""
Скрипт инициализации Superset для RAG платформы
"""
import os
import sys
import logging
from datetime import datetime

# Добавляем путь к Superset
sys.path.append('/app')

from superset import db
from superset.models.core import Database
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.models.datasource import Datasource
from superset.connectors.sqla.models import SqlaTable, TableColumn
from superset.utils.core import get_example_default_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_clickhouse_database():
    """Создание подключения к ClickHouse"""
    try:
        # Проверяем, существует ли уже подключение
        existing_db = db.session.query(Database).filter_by(
            database_name='ClickHouse RAG Metrics'
        ).first()
        
        if existing_db:
            logger.info("ClickHouse database connection already exists")
            return existing_db
        
        # Создаем новое подключение
        clickhouse_uri = os.environ.get(
            'CLICKHOUSE_URI',
            'clickhouse://default@clickhouse:8123/rag'
        )
        
        database = Database(
            database_name='ClickHouse RAG Metrics',
            sqlalchemy_uri=clickhouse_uri,
            extra='{"engine": "clickhouse"}',
            allow_dml=False,
            allow_run_async=True,
            expose_in_sqllab=True
        )
        
        db.session.add(database)
        db.session.commit()
        
        logger.info("ClickHouse database connection created successfully")
        return database
        
    except Exception as e:
        logger.error(f"Error creating ClickHouse database: {e}")
        db.session.rollback()
        return None


def create_datasources(database):
    """Создание источников данных"""
    datasources = []
    
    try:
        # Таблица метрик системы
        system_metrics_table = SqlaTable(
            table_name='system_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.system_metrics',
            is_managed_externally=False,
            external_url='',
            description='Системные метрики производительности'
        )
        db.session.add(system_metrics_table)
        datasources.append(system_metrics_table)
        
        # Таблица метрик качества поиска
        search_quality_table = SqlaTable(
            table_name='search_quality_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.search_quality_metrics',
            is_managed_externally=False,
            external_url='',
            description='Метрики качества поиска и ответов'
        )
        db.session.add(search_quality_table)
        datasources.append(search_quality_table)
        
        # Таблица метрик использования ресурсов
        resource_usage_table = SqlaTable(
            table_name='resource_usage_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.resource_usage_metrics',
            is_managed_externally=False,
            external_url='',
            description='Метрики использования ресурсов системы'
        )
        db.session.add(resource_usage_table)
        datasources.append(resource_usage_table)
        
        # Таблица метрик поиска
        search_metrics_table = SqlaTable(
            table_name='search_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.search_metrics',
            is_managed_externally=False,
            external_url='',
            description='Метрики поисковых запросов'
        )
        db.session.add(search_metrics_table)
        datasources.append(search_metrics_table)
        
        # Таблица метрик чата
        chat_metrics_table = SqlaTable(
            table_name='chat_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.chat_metrics',
            is_managed_externally=False,
            external_url='',
            description='Метрики чат-сессий'
        )
        db.session.add(chat_metrics_table)
        datasources.append(chat_metrics_table)
        
        # Таблица алертов
        alerts_table = SqlaTable(
            table_name='alerts',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.alerts',
            is_managed_externally=False,
            external_url='',
            description='Система алертов и уведомлений'
        )
        db.session.add(alerts_table)
        datasources.append(alerts_table)
        
        # Таблица метрик API
        api_metrics_table = SqlaTable(
            table_name='api_metrics',
            database=database,
            schema='rag',
            sql='SELECT * FROM rag.api_metrics',
            is_managed_externally=False,
            external_url='',
            description='Метрики API запросов'
        )
        db.session.add(api_metrics_table)
        datasources.append(api_metrics_table)
        
        db.session.commit()
        logger.info(f"Created {len(datasources)} datasources")
        
        return datasources
        
    except Exception as e:
        logger.error(f"Error creating datasources: {e}")
        db.session.rollback()
        return []


def create_columns_for_datasources(datasources):
    """Создание колонок для источников данных"""
    try:
        # Определяем колонки для каждой таблицы
        table_columns = {
            'system_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время метрики'},
                {'column_name': 'service', 'type': 'VARCHAR', 'description': 'Название сервиса'},
                {'column_name': 'metric_name', 'type': 'VARCHAR', 'description': 'Название метрики'},
                {'column_name': 'metric_value', 'type': 'FLOAT', 'description': 'Значение метрики'},
                {'column_name': 'metric_unit', 'type': 'VARCHAR', 'description': 'Единица измерения'},
            ],
            'search_quality_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время метрики'},
                {'column_name': 'tenant_id', 'type': 'VARCHAR', 'description': 'ID тенанта'},
                {'column_name': 'query_id', 'type': 'VARCHAR', 'description': 'ID запроса'},
                {'column_name': 'relevance_score', 'type': 'FLOAT', 'description': 'Релевантность'},
                {'column_name': 'precision_score', 'type': 'FLOAT', 'description': 'Точность'},
                {'column_name': 'recall_score', 'type': 'FLOAT', 'description': 'Полнота'},
                {'column_name': 'f1_score', 'type': 'FLOAT', 'description': 'F1-мера'},
                {'column_name': 'response_quality', 'type': 'FLOAT', 'description': 'Качество ответа'},
            ],
            'resource_usage_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время метрики'},
                {'column_name': 'service', 'type': 'VARCHAR', 'description': 'Название сервиса'},
                {'column_name': 'cpu_usage_percent', 'type': 'FLOAT', 'description': 'Использование CPU (%)'},
                {'column_name': 'memory_usage_mb', 'type': 'INTEGER', 'description': 'Использование памяти (MB)'},
                {'column_name': 'disk_usage_mb', 'type': 'INTEGER', 'description': 'Использование диска (MB)'},
                {'column_name': 'active_connections', 'type': 'INTEGER', 'description': 'Активные соединения'},
            ],
            'search_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время запроса'},
                {'column_name': 'tenant_id', 'type': 'VARCHAR', 'description': 'ID тенанта'},
                {'column_name': 'query_text', 'type': 'TEXT', 'description': 'Текст запроса'},
                {'column_name': 'response_time_ms', 'type': 'INTEGER', 'description': 'Время ответа (мс)'},
                {'column_name': 'results_count', 'type': 'INTEGER', 'description': 'Количество результатов'},
                {'column_name': 'success', 'type': 'BOOLEAN', 'description': 'Успешность запроса'},
            ],
            'chat_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время сессии'},
                {'column_name': 'tenant_id', 'type': 'VARCHAR', 'description': 'ID тенанта'},
                {'column_name': 'session_id', 'type': 'VARCHAR', 'description': 'ID сессии'},
                {'column_name': 'messages_count', 'type': 'INTEGER', 'description': 'Количество сообщений'},
                {'column_name': 'response_time_ms', 'type': 'INTEGER', 'description': 'Время ответа (мс)'},
                {'column_name': 'success', 'type': 'BOOLEAN', 'description': 'Успешность сессии'},
            ],
            'alerts': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время алерта'},
                {'column_name': 'alert_id', 'type': 'VARCHAR', 'description': 'ID алерта'},
                {'column_name': 'alert_type', 'type': 'VARCHAR', 'description': 'Тип алерта'},
                {'column_name': 'severity', 'type': 'VARCHAR', 'description': 'Серьезность'},
                {'column_name': 'service', 'type': 'VARCHAR', 'description': 'Сервис'},
                {'column_name': 'message', 'type': 'TEXT', 'description': 'Сообщение'},
                {'column_name': 'status', 'type': 'VARCHAR', 'description': 'Статус'},
            ],
            'api_metrics': [
                {'column_name': 'timestamp', 'type': 'DATETIME', 'description': 'Время запроса'},
                {'column_name': 'endpoint', 'type': 'VARCHAR', 'description': 'Эндпоинт'},
                {'column_name': 'method', 'type': 'VARCHAR', 'description': 'HTTP метод'},
                {'column_name': 'status_code', 'type': 'INTEGER', 'description': 'Код ответа'},
                {'column_name': 'response_time_ms', 'type': 'INTEGER', 'description': 'Время ответа (мс)'},
                {'column_name': 'user_id', 'type': 'VARCHAR', 'description': 'ID пользователя'},
            ]
        }
        
        for datasource in datasources:
            table_name = datasource.table_name
            if table_name in table_columns:
                for col_def in table_columns[table_name]:
                    column = TableColumn(
                        table=datasource,
                        column_name=col_def['column_name'],
                        type=col_def['type'],
                        description=col_def['description'],
                        is_dttm=False,
                        is_active=True
                    )
                    db.session.add(column)
        
        db.session.commit()
        logger.info("Created columns for all datasources")
        
    except Exception as e:
        logger.error(f"Error creating columns: {e}")
        db.session.rollback()


def main():
    """Основная функция инициализации"""
    logger.info("Starting Superset initialization for RAG platform...")
    
    try:
        # Создаем подключение к ClickHouse
        database = create_clickhouse_database()
        if not database:
            logger.error("Failed to create ClickHouse database connection")
            return False
        
        # Создаем источники данных
        datasources = create_datasources(database)
        if not datasources:
            logger.error("Failed to create datasources")
            return False
        
        # Создаем колонки
        create_columns_for_datasources(datasources)
        
        logger.info("Superset initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during Superset initialization: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
