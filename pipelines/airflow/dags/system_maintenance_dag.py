"""
DAG для мониторинга и очистки системы RAG
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.models import Variable
import os
import logging
import json
import shutil
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
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    'catchup': False
}

# Создаем DAG
dag = DAG(
    'system_maintenance',
    default_args=default_args,
    description='Мониторинг и очистка системы RAG',
    schedule_interval='0 2 * * *',  # Каждый день в 2:00
    max_active_runs=1,
    tags=['rag', 'maintenance', 'monitoring', 'cleanup']
)

def check_system_health(**context):
    """Проверяет состояние системы"""
    try:
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Проверка дискового пространства
        disk_health = check_disk_space()
        health_report['checks']['disk'] = disk_health
        
        if disk_health['usage_percent'] > 90:
            health_report['warnings'].append(f"High disk usage: {disk_health['usage_percent']:.1f}%")
        elif disk_health['usage_percent'] > 95:
            health_report['status'] = 'warning'
            health_report['errors'].append(f"Critical disk usage: {disk_health['usage_percent']:.1f}%")
        
        # Проверка памяти
        memory_health = check_memory_usage()
        health_report['checks']['memory'] = memory_health
        
        if memory_health['usage_percent'] > 85:
            health_report['warnings'].append(f"High memory usage: {memory_health['usage_percent']:.1f}%")
        
        # Проверка подключений к БД
        db_health = check_database_connections()
        health_report['checks']['database'] = db_health
        
        if not db_health['postgres_accessible']:
            health_report['status'] = 'error'
            health_report['errors'].append("PostgreSQL connection failed")
        
        # Проверка RAG Core
        rag_health = check_rag_core_health()
        health_report['checks']['rag_core'] = rag_health
        
        if not rag_health['core_accessible']:
            health_report['warnings'].append("RAG Core not accessible")
        
        # Проверка временных файлов
        temp_files_health = check_temporary_files()
        health_report['checks']['temp_files'] = temp_files_health
        
        if temp_files_health['total_size_mb'] > 1000:  # > 1GB
            health_report['warnings'].append(f"Large temporary files: {temp_files_health['total_size_mb']:.1f} MB")
        
        # Сохраняем отчет в XCom
        context['task_instance'].xcom_push(key='health_report', value=health_report)
        
        # Логируем результаты
        logger.info(f"System health check completed. Status: {health_report['status']}")
        if health_report['warnings']:
            logger.warning(f"Warnings: {health_report['warnings']}")
        if health_report['errors']:
            logger.error(f"Errors: {health_report['errors']}")
        
        return health_report
        
    except Exception as e:
        logger.error(f"Error during system health check: {e}")
        raise

def check_disk_space():
    """Проверяет использование дискового пространства"""
    try:
        import shutil
        
        # Проверяем основные директории
        directories = [
            "/opt/airflow",
            "/opt/airflow/logs",
            "/opt/airflow/temp",
            "/opt/airflow/rag_core"
        ]
        
        total_usage = 0
        total_size = 0
        
        for directory in directories:
            if os.path.exists(directory):
                try:
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_usage += os.path.getsize(file_path)
                            except (OSError, IOError):
                                pass
                except (OSError, IOError):
                    pass
        
        # Получаем общую информацию о диске
        total, used, free = shutil.disk_usage("/opt/airflow")
        
        return {
            'total_gb': total // (1024**3),
            'used_gb': used // (1024**3),
            'free_gb': free // (1024**3),
            'usage_percent': (used / total) * 100,
            'airflow_usage_mb': total_usage // (1024**2)
        }
        
    except Exception as e:
        logger.warning(f"Error checking disk space: {e}")
        return {'error': str(e)}

def check_memory_usage():
    """Проверяет использование памяти"""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total_gb': memory.total // (1024**3),
            'available_gb': memory.available // (1024**3),
            'used_gb': memory.used // (1024**3),
            'usage_percent': memory.percent,
            'swap_total_gb': swap.total // (1024**3),
            'swap_used_gb': swap.used // (1024**3),
            'swap_usage_percent': (swap.used / swap.total * 100) if swap.total > 0 else 0
        }
        
    except Exception as e:
        logger.warning(f"Error checking memory usage: {e}")
        return {'error': str(e)}

def check_database_connections():
    """Проверяет подключения к базам данных"""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Получаем конфигурацию
        pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
        
        # Парсим DSN
        parsed = urlparse(pg_dsn.replace('postgresql://', 'http://'))
        host = parsed.hostname
        port = parsed.port or 5432
        username = parsed.username
        password = parsed.password
        database = parsed.path.lstrip('/')
        
        # Тестируем подключение
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            connect_timeout=5
        )
        
        # Проверяем доступность таблиц
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'postgres_accessible': True,
            'host': host,
            'port': port,
            'database': database,
            'table_count': table_count
        }
        
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return {
            'postgres_accessible': False,
            'error': str(e)
        }

def check_rag_core_health():
    """Проверяет состояние RAG Core"""
    try:
        # Проверяем доступность модулей
        import sys
        rag_core_path = "/opt/airflow/rag_core"
        
        if not os.path.exists(rag_core_path):
            return {
                'core_accessible': False,
                'error': 'RAG Core directory not found'
            }
        
        # Проверяем основные файлы
        required_files = [
            'rag_core/__init__.py',
            'rag_core/rag_pipeline.py',
            'rag_core/vectorstore/pgvector_store.py',
            'rag_core/parsers/document_parser.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(rag_core_path, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)
        
        if missing_files:
            return {
                'core_accessible': False,
                'error': f'Missing files: {missing_files}'
            }
        
        # Проверяем размер директории
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(rag_core_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except (OSError, IOError):
                    pass
        
        return {
            'core_accessible': True,
            'total_size_mb': total_size // (1024**2),
            'file_count': file_count,
            'directory': rag_core_path
        }
        
    except Exception as e:
        logger.warning(f"Error checking RAG Core health: {e}")
        return {
            'core_accessible': False,
            'error': str(e)
        }

def check_temporary_files():
    """Проверяет временные файлы"""
    try:
        temp_dirs = [
            "/opt/airflow/temp",
            "/opt/airflow/logs",
            "/tmp"
        ]
        
        total_size = 0
        file_count = 0
        old_files = 0
        
        current_time = datetime.now()
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            total_size += file_size
                            file_count += 1
                            
                            # Файлы старше 7 дней
                            if (current_time - file_time).days > 7:
                                old_files += 1
                                
                        except (OSError, IOError):
                            pass
        
        return {
            'total_size_mb': total_size // (1024**2),
            'file_count': file_count,
            'old_files_count': old_files,
            'old_files_threshold_days': 7
        }
        
    except Exception as e:
        logger.warning(f"Error checking temporary files: {e}")
        return {'error': str(e)}

def cleanup_old_logs(**context):
    """Очищает старые логи"""
    try:
        cleanup_report = {
            'timestamp': datetime.now().isoformat(),
            'logs_cleaned': 0,
            'size_freed_mb': 0,
            'errors': []
        }
        
        # Получаем отчет о здоровье системы
        health_report = context['task_instance'].xcom_pull(key='health_report', task_ids='check_system_health')
        
        if not health_report or health_report.get('status') == 'error':
            logger.warning("Skipping cleanup due to system health issues")
            return cleanup_report
        
        # Очищаем логи старше 30 дней
        log_dirs = [
            "/opt/airflow/logs",
            "/opt/airflow/temp"
        ]
        
        current_time = datetime.now()
        cutoff_date = current_time - timedelta(days=30)
        
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                try:
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                                
                                if file_time < cutoff_date:
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    
                                    cleanup_report['logs_cleaned'] += 1
                                    cleanup_report['size_freed_mb'] += file_size // (1024**2)
                                    
                            except (OSError, IOError) as e:
                                cleanup_report['errors'].append(f"Error cleaning {file_path}: {e}")
                                
                except Exception as e:
                    cleanup_report['errors'].append(f"Error processing directory {log_dir}: {e}")
        
        # Очищаем старые метрики
        cleanup_old_metrics()
        
        # Сохраняем отчет в XCom
        context['task_instance'].xcom_push(key='cleanup_report', value=cleanup_report)
        
        logger.info(f"Cleanup completed. Cleaned {cleanup_report['logs_cleaned']} files, freed {cleanup_report['size_freed_mb']} MB")
        
        return cleanup_report
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

def cleanup_old_metrics():
    """Очищает старые метрики"""
    try:
        metrics_file = "/opt/airflow/metrics_history.json"
        
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                history = json.load(f)
            
            # Ограничиваем историю последними 500 записями
            if len(history.get('metrics', [])) > 500:
                history['metrics'] = history['metrics'][-500:]
                
                with open(metrics_file, 'w') as f:
                    json.dump(history, f, indent=2)
                
                logger.info("Cleaned old metrics, kept last 500 records")
                
    except Exception as e:
        logger.warning(f"Error cleaning old metrics: {e}")

def optimize_database(**context):
    """Оптимизирует базу данных"""
    try:
        optimization_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'operations': [],
            'errors': []
        }
        
        # Получаем отчет о здоровье системы
        health_report = context['task_instance'].xcom_push(key='health_report', task_ids='check_system_health')
        
        if not health_report or health_report.get('status') == 'error':
            logger.warning("Skipping database optimization due to system health issues")
            optimization_report['status'] = 'skipped'
            return optimization_report
        
        try:
            # Импортируем RAG Core
            import sys
            sys.path.append('/opt/airflow/rag_core')
            
            from rag_core.vectorstore.pgvector_store import PgVectorStore
            
            # Получаем конфигурацию
            pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
            
            # Создаем подключение к векторному хранилищу
            vector_store = PgVectorStore(pg_dsn)
            
            # Оптимизируем индексы
            vector_store.optimize_indexes()
            optimization_report['operations'].append('index_optimization')
            
            # Анализируем таблицы
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(pg_dsn.replace('postgresql://', 'http://'))
            host = parsed.hostname
            port = parsed.port or 5432
            username = parsed.username
            password = parsed.password
            database = parsed.path.lstrip('/')
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database
            )
            
            cursor = conn.cursor()
            
            # ANALYZE для всех таблиц
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename IN ('documents', 'chunks', 'embeddings', 'tenants', 'users')
            """)
            
            tables = cursor.fetchall()
            
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE {table[0]}")
                    optimization_report['operations'].append(f'analyze_{table[0]}')
                except Exception as e:
                    optimization_report['errors'].append(f"Error analyzing {table[0]}: {e}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            optimization_report['status'] = 'error'
            optimization_report['errors'].append(f"Database optimization failed: {e}")
            logger.error(f"Database optimization failed: {e}")
        
        # Сохраняем отчет в XCom
        context['task_instance'].xcom_push(key='optimization_report', value=optimization_report)
        
        return optimization_report
        
    except Exception as e:
        logger.error(f"Error during database optimization: {e}")
        raise

def generate_maintenance_report(**context):
    """Генерирует отчет о техническом обслуживании"""
    try:
        # Получаем все отчеты
        health_report = context['task_instance'].xcom_pull(key='health_report', task_ids='check_system_health')
        cleanup_report = context['task_instance'].xcom_pull(key='cleanup_report', task_ids='cleanup_old_logs')
        optimization_report = context['task_instance'].xcom_pull(key='optimization_report', task_ids='optimize_database')
        
        # Формируем общий отчет
        maintenance_report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'system_status': health_report.get('status', 'unknown') if health_report else 'unknown',
                'cleanup_performed': bool(cleanup_report),
                'optimization_performed': bool(optimization_report)
            },
            'health_check': health_report,
            'cleanup': cleanup_report,
            'optimization': optimization_report,
            'recommendations': generate_recommendations(health_report, cleanup_report, optimization_report)
        }
        
        # Сохраняем отчет в XCom
        context['task_instance'].xcom_push(key='maintenance_report', value=maintenance_report)
        
        # Логируем отчет
        logger.info("Maintenance Report:")
        logger.info(f"  System status: {maintenance_report['summary']['system_status']}")
        logger.info(f"  Cleanup performed: {maintenance_report['summary']['cleanup_performed']}")
        logger.info(f"  Optimization performed: {maintenance_report['summary']['optimization_performed']}")
        
        if maintenance_report['recommendations']:
            logger.info("  Recommendations:")
            for rec in maintenance_report['recommendations']:
                logger.info(f"    - {rec}")
        
        return maintenance_report
        
    except Exception as e:
        logger.error(f"Error generating maintenance report: {e}")
        raise

def generate_recommendations(health_report, cleanup_report, optimization_report):
    """Генерирует рекомендации на основе отчетов"""
    recommendations = []
    
    if not health_report:
        recommendations.append("System health check failed - investigate immediately")
        return recommendations
    
    # Рекомендации по диску
    if 'disk' in health_report.get('checks', {}):
        disk = health_report['checks']['disk']
        if disk.get('usage_percent', 0) > 90:
            recommendations.append("High disk usage - consider cleanup or expansion")
        if disk.get('airflow_usage_mb', 0) > 500:
            recommendations.append("Large Airflow directory - review log retention policies")
    
    # Рекомендации по памяти
    if 'memory' in health_report.get('checks', {}):
        memory = health_report['checks']['memory']
        if memory.get('usage_percent', 0) > 85:
            recommendations.append("High memory usage - monitor for memory leaks")
    
    # Рекомендации по базе данных
    if 'database' in health_report.get('checks', {}):
        db = health_report['checks']['database']
        if not db.get('postgres_accessible', True):
            recommendations.append("Database connection issues - check connectivity and credentials")
    
    # Рекомендации по очистке
    if cleanup_report:
        if cleanup_report.get('logs_cleaned', 0) > 100:
            recommendations.append("Many old logs cleaned - consider adjusting retention policies")
        if cleanup_report.get('errors'):
            recommendations.append("Cleanup errors detected - review file permissions and paths")
    
    # Рекомендации по оптимизации
    if optimization_report:
        if optimization_report.get('status') == 'error':
            recommendations.append("Database optimization failed - check database health and permissions")
        if len(optimization_report.get('operations', [])) > 0:
            recommendations.append("Database optimization completed successfully")
    
    # Общие рекомендации
    if health_report.get('status') == 'warning':
        recommendations.append("System showing warning signs - monitor closely")
    elif health_report.get('status') == 'error':
        recommendations.append("System in error state - immediate attention required")
    
    return recommendations

# Определяем задачи
start_task = EmptyOperator(task_id='start', dag=dag)

health_check_task = PythonOperator(
    task_id='check_system_health',
    python_callable=check_system_health,
    dag=dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_old_logs',
    python_callable=cleanup_old_logs,
    dag=dag
)

optimize_task = PythonOperator(
    task_id='optimize_database',
    python_callable=optimize_database,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_maintenance_report',
    python_callable=generate_maintenance_report,
    dag=dag
)

end_task = EmptyOperator(task_id='end', dag=dag)

# Определяем зависимости
start_task >> health_check_task >> [cleanup_task, optimize_task] >> report_task >> end_task
