"""
DAG для автоматической загрузки и обработки документов
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.models import Variable
import os
import logging
from pathlib import Path
import hashlib
import json

# Настройка логирования
logger = logging.getLogger(__name__)

# Параметры DAG
default_args = {
    'owner': 'rag-platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Создаем DAG
dag = DAG(
    'ingest_documents',
    default_args=default_args,
    description='Автоматическая загрузка и обработка документов',
    schedule_interval='*/15 * * * *',  # Каждые 15 минут
    max_active_runs=1,
    tags=['rag', 'documents', 'ingest']
)

def discover_new_documents(**context):
    """Обнаруживает новые документы в inbox каталоге"""
    try:
        # Получаем путь к inbox каталогу
        inbox_path = Variable.get("inbox_path", default_var="/opt/airflow/inbox")
        inbox_dir = Path(inbox_path)
        
        if not inbox_dir.exists():
            logger.error(f"Inbox directory {inbox_path} does not exist")
            return []
        
        # Получаем список уже обработанных документов
        processed_files = get_processed_files()
        
        # Ищем новые файлы
        new_files = []
        supported_extensions = {'.pdf', '.docx', '.xlsx', '.html', '.htm', '.eml'}
        
        for file_path in inbox_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                file_hash = calculate_file_hash(file_path)
                
                if file_hash not in processed_files:
                    new_files.append({
                        'path': str(file_path),
                        'hash': file_hash,
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix.lower(),
                        'discovered_at': datetime.now().isoformat()
                    })
                    logger.info(f"Discovered new file: {file_path}")
        
        # Сохраняем информацию о новых файлах в XCom
        context['task_instance'].xcom_push(key='new_documents', value=new_files)
        
        logger.info(f"Discovered {len(new_files)} new documents")
        return new_files
        
    except Exception as e:
        logger.error(f"Error discovering documents: {e}")
        raise

def get_processed_files():
    """Получает список уже обработанных файлов"""
    try:
        # В реальной реализации здесь будет запрос к БД
        # Пока используем простой файл
        processed_file = "/opt/airflow/processed_files.json"
        
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                data = json.load(f)
                return set(data.get('processed_hashes', []))
        return set()
        
    except Exception as e:
        logger.warning(f"Error getting processed files: {e}")
        return set()

def calculate_file_hash(file_path):
    """Вычисляет SHA256 хеш файла"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def validate_document(**context):
    """Валидирует обнаруженные документы"""
    try:
        # Получаем список новых документов
        new_documents = context['task_instance'].xcom_pull(key='new_documents', task_ids='discover_documents')
        
        if not new_documents:
            logger.info("No new documents to validate")
            return []
        
        valid_documents = []
        
        for doc in new_documents:
            file_path = Path(doc['path'])
            
            # Проверяем существование файла
            if not file_path.exists():
                logger.warning(f"File {file_path} no longer exists")
                continue
            
            # Проверяем размер файла
            if doc['size'] == 0:
                logger.warning(f"File {file_path} is empty")
                continue
            
            # Проверяем доступность для чтения
            if not os.access(file_path, os.R_OK):
                logger.warning(f"File {file_path} is not readable")
                continue
            
            # Проверяем MIME тип
            mime_type = get_mime_type(file_path)
            if mime_type:
                doc['mime_type'] = mime_type
                valid_documents.append(doc)
                logger.info(f"Document {file_path} validated successfully")
            else:
                logger.warning(f"Could not determine MIME type for {file_path}")
        
        # Сохраняем валидные документы
        context['task_instance'].xcom_push(key='valid_documents', value=valid_documents)
        
        logger.info(f"Validated {len(valid_documents)} documents")
        return valid_documents
        
    except Exception as e:
        logger.error(f"Error validating documents: {e}")
        raise

def get_mime_type(file_path):
    """Определяет MIME тип файла"""
    try:
        import magic
        
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
        
    except ImportError:
        # Fallback к расширениям файлов
        extension_mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.eml': 'message/rfc822'
        }
        
        return extension_mime_types.get(file_path.suffix.lower(), 'application/octet-stream')

def process_document_with_rag(**context):
    """Обрабатывает документ с помощью RAG Core"""
    try:
        # Получаем валидные документы
        valid_documents = context['task_instance'].xcom_pull(key='valid_documents', task_ids='validate_documents')
        
        if not valid_documents:
            logger.info("No valid documents to process")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core import RAGPipeline
        
        # Получаем конфигурацию
        pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
        
        # Создаем RAG pipeline
        rag_pipeline = RAGPipeline(pg_dsn)
        
        processed_documents = []
        
        for doc in valid_documents:
            try:
                logger.info(f"Processing document: {doc['path']}")
                
                # Обрабатываем документ
                result = rag_pipeline.process_document(Path(doc['path']))
                
                # Добавляем результат обработки
                doc['processing_result'] = result
                doc['processed_at'] = datetime.now().isoformat()
                doc['status'] = 'success'
                
                processed_documents.append(doc)
                logger.info(f"Document {doc['path']} processed successfully")
                
            except Exception as e:
                logger.error(f"Error processing document {doc['path']}: {e}")
                doc['status'] = 'error'
                doc['error_message'] = str(e)
                doc['processed_at'] = datetime.now().isoformat()
                processed_documents.append(doc)
        
        # Сохраняем результаты обработки
        context['task_instance'].xcom_push(key='processed_documents', value=processed_documents)
        
        logger.info(f"Processed {len(processed_documents)} documents")
        return processed_documents
        
    except Exception as e:
        logger.error(f"Error in RAG processing: {e}")
        raise

def update_processing_status(**context):
    """Обновляет статус обработки документов"""
    try:
        # Получаем обработанные документы
        processed_documents = context['task_instance'].xcom_pull(key='processed_documents', task_ids='process_documents')
        
        if not processed_documents:
            logger.info("No documents to update status")
            return
        
        # В реальной реализации здесь будет обновление БД
        # Пока просто логируем
        
        success_count = sum(1 for doc in processed_documents if doc['status'] == 'success')
        error_count = sum(1 for doc in processed_documents if doc['status'] == 'error')
        
        logger.info(f"Processing completed: {success_count} success, {error_count} errors")
        
        # Обновляем список обработанных файлов
        update_processed_files(processed_documents)
        
    except Exception as e:
        logger.error(f"Error updating processing status: {e}")
        raise

def update_processed_files(processed_documents):
    """Обновляет список обработанных файлов"""
    try:
        processed_file = "/opt/airflow/processed_files.json"
        
        # Загружаем существующий список
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                data = json.load(f)
        else:
            data = {'processed_hashes': [], 'documents': []}
        
        # Добавляем новые хеши
        for doc in processed_documents:
            if doc['hash'] not in data['processed_hashes']:
                data['processed_hashes'].append(doc['hash'])
            
            # Добавляем информацию о документе
            doc_info = {
                'hash': doc['hash'],
                'path': doc['path'],
                'status': doc['status'],
                'processed_at': doc['processed_at']
            }
            
            if 'error_message' in doc:
                doc_info['error_message'] = doc['error_message']
            
            data['documents'].append(doc_info)
        
        # Сохраняем обновленный список
        with open(processed_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Updated processed files list with {len(processed_documents)} documents")
        
    except Exception as e:
        logger.error(f"Error updating processed files: {e}")

def cleanup_temp_files(**context):
    """Очищает временные файлы"""
    try:
        # Получаем обработанные документы
        processed_documents = context['task_instance'].xcom_pull(key='processed_documents', task_ids='process_documents')
        
        if not processed_documents:
            logger.info("No documents to cleanup")
            return
        
        # В реальной реализации здесь может быть очистка временных файлов
        # Пока просто логируем
        
        logger.info("Cleanup completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        raise

def generate_processing_report(**context):
    """Генерирует отчет об обработке"""
    try:
        # Получаем все данные
        new_documents = context['task_instance'].xcom_pull(key='new_documents', task_ids='discover_documents')
        valid_documents = context['task_instance'].xcom_pull(key='valid_documents', task_ids='validate_documents')
        processed_documents = context['task_instance'].xcom_pull(key='processed_documents', task_ids='process_documents')
        
        # Формируем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'discovery': {
                'total_found': len(new_documents) if new_documents else 0
            },
            'validation': {
                'total_valid': len(valid_documents) if valid_documents else 0,
                'total_invalid': (len(new_documents) if new_documents else 0) - (len(valid_documents) if valid_documents else 0)
            },
            'processing': {
                'total_processed': len(processed_documents) if processed_documents else 0,
                'success_count': sum(1 for doc in processed_documents if doc and doc.get('status') == 'success') if processed_documents else 0,
                'error_count': sum(1 for doc in processed_documents if doc and doc.get('status') == 'error') if processed_documents else 0
            }
        }
        
        # Сохраняем отчет
        context['task_instance'].xcom_push(key='processing_report', value=report)
        
        # Логируем отчет
        logger.info("Processing Report:")
        logger.info(f"  Discovery: {report['discovery']['total_found']} documents found")
        logger.info(f"  Validation: {report['validation']['total_valid']} valid, {report['validation']['total_invalid']} invalid")
        logger.info(f"  Processing: {report['processing']['success_count']} success, {report['processing']['error_count']} errors")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

# Определяем задачи
start_task = EmptyOperator(task_id='start', dag=dag)

discover_task = PythonOperator(
    task_id='discover_documents',
    python_callable=discover_new_documents,
    dag=dag
)

validate_task = PythonOperator(
    task_id='validate_documents',
    python_callable=validate_document,
    dag=dag
)

process_task = PythonOperator(
    task_id='process_documents',
    python_callable=process_document_with_rag,
    dag=dag
)

update_status_task = PythonOperator(
    task_id='update_processing_status',
    python_callable=update_processing_status,
    dag=dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_processing_report,
    dag=dag
)

end_task = EmptyOperator(task_id='end', dag=dag)

# Определяем зависимости
start_task >> discover_task >> validate_task >> process_task >> update_status_task >> cleanup_task >> report_task >> end_task
