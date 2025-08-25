"""
DAG для синхронизации метрик в ClickHouse
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.models import Variable
import os
import logging
import json
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)

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

# Создаем DAG
dag = DAG(
    'sync_clickhouse_metrics',
    default_args=default_args,
    description='Синхронизация метрик RAG системы в ClickHouse',
    schedule_interval='0 */2 * * *',  # Каждые 2 часа
    max_active_runs=1,
    tags=['rag', 'metrics', 'clickhouse', 'monitoring']
)

def collect_rag_metrics(**context):
    """Собирает метрики RAG системы из PostgreSQL"""
    try:
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.vectorstore.pgvector_store import PgVectorStore
        
        # Получаем конфигурацию
        pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
        
        # Создаем подключение к векторному хранилищу
        vector_store = PgVectorStore(pg_dsn)
        
        # Собираем статистику
        stats = vector_store.get_statistics()
        
        # Дополнительные метрики
        additional_metrics = collect_additional_metrics()
        
        # Объединяем метрики
        all_metrics = {
            'timestamp': datetime.now().isoformat(),
            'source': 'rag_system',
            'statistics': stats,
            'additional': additional_metrics
        }
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='rag_metrics', value=all_metrics)
        
        logger.info(f"Collected RAG metrics: {len(stats)} categories")
        return all_metrics
        
    except Exception as e:
        logger.error(f"Error collecting RAG metrics: {e}")
        raise

def collect_additional_metrics():
    """Собирает дополнительные метрики системы"""
    try:
        metrics = {}
        
        # Метрики обработки документов
        processing_file = "/opt/airflow/processed_files.json"
        if os.path.exists(processing_file):
            with open(processing_file, 'r') as f:
                data = json.load(f)
                metrics['document_processing'] = {
                    'total_processed': len(data.get('processed_hashes', [])),
                    'total_documents': len(data.get('documents', [])),
                    'last_processed': data.get('documents', [{}])[-1].get('processed_at') if data.get('documents') else None
                }
        
        # Метрики Airflow DAG
        metrics['airflow_dags'] = {
            'ingest_dag_runs': get_dag_run_count('ingest_documents'),
            'process_dag_runs': get_dag_run_count('process_and_index_documents'),
            'last_successful_run': get_last_successful_run()
        }
        
        # Системные метрики
        metrics['system'] = {
            'disk_usage': get_disk_usage(),
            'memory_usage': get_memory_usage(),
            'uptime': get_system_uptime()
        }
        
        return metrics
        
    except Exception as e:
        logger.warning(f"Error collecting additional metrics: {e}")
        return {}

def get_dag_run_count(dag_id):
    """Получает количество запусков DAG"""
    try:
        # В реальной реализации здесь будет запрос к Airflow метабазе
        # Пока возвращаем заглушку
        return 0
    except Exception:
        return 0

def get_last_successful_run():
    """Получает время последнего успешного запуска"""
    try:
        # В реальной реализации здесь будет запрос к Airflow метабазе
        # Пока возвращаем заглушку
        return datetime.now().isoformat()
    except Exception:
        return datetime.now().isoformat()

def get_disk_usage():
    """Получает информацию об использовании диска"""
    try:
        import shutil
        
        total, used, free = shutil.disk_usage("/opt/airflow")
        return {
            'total_gb': total // (1024**3),
            'used_gb': used // (1024**3),
            'free_gb': free // (1024**3),
            'usage_percent': (used / total) * 100
        }
    except Exception:
        return {}

def get_memory_usage():
    """Получает информацию об использовании памяти"""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total // (1024**3),
            'available_gb': memory.available // (1024**3),
            'used_gb': memory.used // (1024**3),
            'usage_percent': memory.percent
        }
    except Exception:
        return {}

def get_system_uptime():
    """Получает время работы системы"""
    try:
        import psutil
        import time
        
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = uptime_seconds / 3600
        
        return {
            'uptime_hours': uptime_hours,
            'uptime_days': uptime_hours / 24
        }
    except Exception:
        return {}

def collect_search_metrics(**context):
    """Собирает метрики поиска и использования"""
    try:
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.vectorstore.pgvector_store import PgVectorStore
        
        # Получаем конфигурацию
        pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
        
        # Создаем подключение к векторному хранилищу
        vector_store = PgVectorStore(pg_dsn)
        
        # В реальной реализации здесь будет сбор метрик поиска
        # Пока создаем заглушку
        search_metrics = {
            'timestamp': datetime.now().isoformat(),
            'source': 'search_analytics',
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_response_time_ms': 0,
            'popular_queries': [],
            'search_by_type': {
                'semantic': 0,
                'keyword': 0,
                'hybrid': 0
            }
        }
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='search_metrics', value=search_metrics)
        
        logger.info("Collected search metrics")
        return search_metrics
        
    except Exception as e:
        logger.error(f"Error collecting search metrics: {e}")
        raise

def collect_quality_metrics(**context):
    """Собирает метрики качества RAG системы"""
    try:
        # В реальной реализации здесь будет анализ качества ответов
        # Пока создаем заглушку
        quality_metrics = {
            'timestamp': datetime.now().isoformat(),
            'source': 'quality_analytics',
            'answer_relevance': {
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0
            },
            'citation_accuracy': {
                'correct': 0,
                'partially_correct': 0,
                'incorrect': 0
            },
            'user_feedback': {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            },
            'response_completeness': {
                'complete': 0,
                'partial': 0,
                'incomplete': 0
            }
        }
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='quality_metrics', value=quality_metrics)
        
        logger.info("Collected quality metrics")
        return quality_metrics
        
    except Exception as e:
        logger.error(f"Error collecting quality metrics: {e}")
        raise

def transform_metrics_for_clickhouse(**context):
    """Трансформирует метрики для ClickHouse"""
    try:
        # Получаем все метрики
        rag_metrics = context['task_instance'].xcom_pull(key='rag_metrics', task_ids='collect_rag_metrics')
        search_metrics = context['task_instance'].xcom_pull(key='search_metrics', task_ids='collect_search_metrics')
        quality_metrics = context['task_instance'].xcom_pull(key='quality_metrics', task_ids='collect_quality_metrics')
        
        # Трансформируем в формат для ClickHouse
        clickhouse_records = []
        
        # RAG метрики
        if rag_metrics:
            timestamp = rag_metrics['timestamp']
            
            # Документы
            if 'statistics' in rag_metrics and 'documents' in rag_metrics['statistics']:
                doc_stats = rag_metrics['statistics']['documents']
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'documents',
                    'metric_name': 'total_documents',
                    'metric_value': doc_stats.get('total', 0),
                    'metric_unit': 'count',
                    'source': 'rag_system'
                })
                
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'documents',
                    'metric_name': 'total_size_bytes',
                    'metric_value': doc_stats.get('total_size_bytes', 0),
                    'metric_unit': 'bytes',
                    'source': 'rag_system'
                })
            
            # Чанки
            if 'statistics' in rag_metrics and 'chunks' in rag_metrics['statistics']:
                chunk_stats = rag_metrics['statistics']['chunks']
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'chunks',
                    'metric_name': 'total_chunks',
                    'metric_value': chunk_stats.get('total', 0),
                    'metric_unit': 'count',
                    'source': 'rag_system'
                })
            
            # Эмбеддинги
            if 'statistics' in rag_metrics and 'embeddings' in rag_metrics['statistics']:
                embedding_stats = rag_metrics['statistics']['embeddings']
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'embeddings',
                    'metric_name': 'total_embeddings',
                    'metric_value': embedding_stats.get('total', 0),
                    'metric_unit': 'count',
                    'source': 'rag_system'
                })
        
        # Поисковые метрики
        if search_metrics:
            timestamp = search_metrics['timestamp']
            
            clickhouse_records.append({
                'timestamp': timestamp,
                'metric_type': 'search',
                'metric_name': 'total_searches',
                'metric_value': search_metrics.get('total_searches', 0),
                'metric_unit': 'count',
                'source': 'search_analytics'
            })
            
            clickhouse_records.append({
                'timestamp': timestamp,
                'metric_type': 'search',
                'metric_name': 'successful_searches',
                'metric_value': search_metrics.get('successful_searches', 0),
                'metric_unit': 'count',
                'source': 'search_analytics'
            })
        
        # Метрики качества
        if quality_metrics:
            timestamp = quality_metrics['timestamp']
            
            # Релевантность ответов
            relevance = quality_metrics.get('answer_relevance', {})
            for level, count in relevance.items():
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'quality',
                    'metric_name': f'answer_relevance_{level}',
                    'metric_value': count,
                    'metric_unit': 'count',
                    'source': 'quality_analytics'
                })
            
            # Точность цитирования
            citation = quality_metrics.get('citation_accuracy', {})
            for level, count in citation.items():
                clickhouse_records.append({
                    'timestamp': timestamp,
                    'metric_type': 'quality',
                    'metric_name': f'citation_accuracy_{level}',
                    'metric_value': count,
                    'metric_unit': 'count',
                    'source': 'quality_analytics'
                })
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='clickhouse_records', value=clickhouse_records)
        
        logger.info(f"Transformed {len(clickhouse_records)} metrics for ClickHouse")
        return clickhouse_records
        
    except Exception as e:
        logger.error(f"Error transforming metrics: {e}")
        raise

def send_metrics_to_clickhouse(**context):
    """Отправляет метрики в ClickHouse"""
    try:
        # Получаем трансформированные метрики
        clickhouse_records = context['task_instance'].xcom_pull(key='clickhouse_records', task_ids='transform_metrics_for_clickhouse')
        
        if not clickhouse_records:
            logger.info("No metrics to send to ClickHouse")
            return
        
        # Получаем конфигурацию ClickHouse
        clickhouse_url = Variable.get("clickhouse_url", default_var="http://clickhouse:8123")
        clickhouse_db = Variable.get("clickhouse_db", default_var="rag")
        
        # В реальной реализации здесь будет отправка в ClickHouse
        # Пока просто логируем
        
        logger.info(f"Sending {len(clickhouse_records)} metrics to ClickHouse")
        
        # Сохраняем метрики локально для демонстрации
        save_metrics_locally(clickhouse_records)
        
        # Сохраняем статус в XCom
        context['task_instance'].xcom_push(key='clickhouse_sync_status', value={
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'records_sent': len(clickhouse_records),
            'destination': f"{clickhouse_url}/{clickhouse_db}"
        })
        
        logger.info("Metrics sent to ClickHouse successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error sending metrics to ClickHouse: {e}")
        
        # Сохраняем статус ошибки
        context['task_instance'].xcom_push(key='clickhouse_sync_status', value={
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error_message': str(e),
            'destination': 'unknown'
        })
        
        raise

def save_metrics_locally(metrics):
    """Сохраняет метрики локально для демонстрации"""
    try:
        metrics_file = "/opt/airflow/metrics_history.json"
        
        # Загружаем существующие метрики
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                history = json.load(f)
        else:
            history = {'metrics': []}
        
        # Добавляем новые метрики
        history['metrics'].extend(metrics)
        
        # Ограничиваем историю последними 1000 записями
        if len(history['metrics']) > 1000:
            history['metrics'] = history['metrics'][-1000:]
        
        # Сохраняем обновленную историю
        with open(metrics_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Saved {len(metrics)} metrics to local history")
        
    except Exception as e:
        logger.warning(f"Error saving metrics locally: {e}")

def generate_metrics_report(**context):
    """Генерирует отчет о синхронизации метрик"""
    try:
        # Получаем все данные
        rag_metrics = context['task_instance'].xcom_pull(key='rag_metrics', task_ids='collect_rag_metrics')
        search_metrics = context['task_instance'].xcom_pull(key='search_metrics', task_ids='collect_search_metrics')
        quality_metrics = context['task_instance'].xcom_pull(key='quality_metrics', task_ids='collect_quality_metrics')
        clickhouse_records = context['task_instance'].xcom_pull(key='clickhouse_records', task_ids='transform_metrics_for_clickhouse')
        sync_status = context['task_instance'].xcom_pull(key='clickhouse_sync_status', task_ids='send_metrics_to_clickhouse')
        
        # Формируем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'sync_status': sync_status,
            'metrics_summary': {
                'rag_metrics_collected': bool(rag_metrics),
                'search_metrics_collected': bool(search_metrics),
                'quality_metrics_collected': bool(quality_metrics),
                'total_clickhouse_records': len(clickhouse_records) if clickhouse_records else 0
            },
            'system_health': {
                'document_count': rag_metrics.get('statistics', {}).get('documents', {}).get('total', 0) if rag_metrics else 0,
                'chunk_count': rag_metrics.get('statistics', {}).get('chunks', {}).get('total', 0) if rag_metrics else 0,
                'embedding_count': rag_metrics.get('statistics', {}).get('embeddings', {}).get('total', 0) if rag_metrics else 0
            }
        }
        
        # Сохраняем отчет
        context['task_instance'].xcom_push(key='metrics_report', value=report)
        
        # Логируем отчет
        logger.info("Metrics Sync Report:")
        logger.info(f"  Sync status: {sync_status.get('status', 'unknown')}")
        logger.info(f"  Records sent: {sync_status.get('records_sent', 0)}")
        logger.info(f"  System health: {report['system_health']}")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating metrics report: {e}")
        raise

# Определяем задачи
start_task = EmptyOperator(task_id='start', dag=dag)

collect_rag_task = PythonOperator(
    task_id='collect_rag_metrics',
    python_callable=collect_rag_metrics,
    dag=dag
)

collect_search_task = PythonOperator(
    task_id='collect_search_metrics',
    python_callable=collect_search_metrics,
    dag=dag
)

collect_quality_task = PythonOperator(
    task_id='collect_quality_metrics',
    python_callable=collect_quality_metrics,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_metrics_for_clickhouse',
    python_callable=transform_metrics_for_clickhouse,
    dag=dag
)

send_clickhouse_task = PythonOperator(
    task_id='send_metrics_to_clickhouse',
    python_callable=send_metrics_to_clickhouse,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_metrics_report',
    python_callable=generate_metrics_report,
    dag=dag
)

end_task = EmptyOperator(task_id='end', dag=dag)

# Определяем зависимости
start_task >> [collect_rag_task, collect_search_task, collect_quality_task] >> transform_task >> send_clickhouse_task >> report_task >> end_task
