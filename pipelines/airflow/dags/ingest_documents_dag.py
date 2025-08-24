"""
DAG для обработки документов в RAG-платформе
Пайплайн: обнаружение → парсинг → OCR → таблицы → чанки → эмбеддинги → upsert
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
import os
import logging

# Настройки по умолчанию
default_args = {
    'owner': 'rag-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Параметры DAG
dag_id = 'ingest_documents_dag'
schedule_interval = '0 */2 * * *'  # Каждые 2 часа
catchup = False

# Пути
INBOX_PATH = '/opt/airflow/inbox'
PROCESSED_PATH = '/opt/airflow/processed'
ERROR_PATH = '/opt/airflow/error'

def discover_new_documents(**context):
    """Обнаружение новых документов в inbox"""
    import os
    from pathlib import Path
    
    inbox = Path(INBOX_PATH)
    if not inbox.exists():
        logging.warning(f"Inbox path {INBOX_PATH} does not exist")
        return []
    
    # Поддерживаемые форматы
    supported_extensions = {'.pdf', '.docx', '.xlsx', '.html', '.eml', '.jpg', '.jpeg', '.png', '.tiff'}
    
    new_docs = []
    for file_path in inbox.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            # Проверяем, не обработан ли уже файл
            processed_file = Path(PROCESSED_PATH) / file_path.name
            if not processed_file.exists():
                new_docs.append(str(file_path))
    
    logging.info(f"Found {len(new_docs)} new documents to process")
    context['task_instance'].xcom_push(key='new_documents', value=new_docs)
    return new_docs

def process_document(document_path: str, **context):
    """Обработка одного документа"""
    from rag_core.parsers.document_parser import DocumentParser
    from rag_core.ocr.ocr_processor import OCRProcessor
    from rag_core.tables.table_extractor import TableExtractor
    from rag_core.vectorstore.pgvector_store import PgVectorStore
    import os
    
    try:
        logging.info(f"Processing document: {document_path}")
        
        # Инициализация компонентов
        parser = DocumentParser()
        ocr_processor = OCRProcessor()
        table_extractor = TableExtractor()
        
        # Получаем DSN из переменных окружения
        pg_dsn = os.getenv('PG_DSN')
        if not pg_dsn:
            raise ValueError("PG_DSN environment variable not set")
        
        vector_store = PgVectorStore(pg_dsn)
        
        # Парсинг документа
        doc_content = parser.parse(document_path)
        
        # OCR для изображений/сканов
        if doc_content.needs_ocr:
            doc_content = ocr_processor.process(doc_content)
        
        # Извлечение таблиц
        tables = table_extractor.extract_tables(doc_content)
        
        # Создание чанков
        chunks = parser.create_chunks(doc_content, chunk_size=1000, overlap=200)
        
        # Генерация эмбеддингов
        embeddings = []
        for chunk in chunks:
            # Здесь будет вызов Ollama для эмбеддингов
            # Пока заглушка
            embedding = [0.0] * 1024  # BGE-M3 размер
            embeddings.append(embedding)
        
        # Upsert в векторное хранилище
        doc_id = vector_store.ensure_document(
            path=document_path,
            sha256=doc_content.sha256,
            title=doc_content.title or os.path.basename(document_path)
        )
        
        # Подготовка payload для chunks
        chunk_payloads = []
        for i, chunk in enumerate(chunks):
            payload = {
                'idx': i,
                'kind': 'text',
                'text': chunk.text,
                'table_html': chunk.table_html if hasattr(chunk, 'table_html') else None,
                'bbox': chunk.bbox if hasattr(chunk, 'bbox') else None,
                'page_no': chunk.page_no if hasattr(chunk, 'page_no') else None
            }
            chunk_payloads.append(payload)
        
        vector_store.upsert_chunks_and_embeddings(doc_id, chunk_payloads, embeddings)
        
        # Перемещение в processed
        os.makedirs(PROCESSED_PATH, exist_ok=True)
        processed_path = os.path.join(PROCESSED_PATH, os.path.basename(document_path))
        os.rename(document_path, processed_path)
        
        logging.info(f"Successfully processed: {document_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error processing {document_path}: {str(e)}")
        
        # Перемещение в error
        os.makedirs(ERROR_PATH, exist_ok=True)
        error_path = os.path.join(ERROR_PATH, os.path.basename(document_path))
        os.rename(document_path, error_path)
        
        raise e

def process_all_documents(**context):
    """Обработка всех обнаруженных документов"""
    new_docs = context['task_instance'].xcom_pull(key='new_documents', task_ids='discover_documents')
    
    if not new_docs:
        logging.info("No new documents to process")
        return
    
    results = []
    for doc_path in new_docs:
        try:
            result = process_document(doc_path, **context)
            results.append(result)
        except Exception as e:
            logging.error(f"Failed to process {doc_path}: {e}")
            results.append(False)
    
    success_count = sum(1 for r in results if r)
    logging.info(f"Processed {success_count}/{len(results)} documents successfully")
    
    return results

def update_metrics(**context):
    """Обновление метрик в ClickHouse"""
    import os
    from clickhouse_connect import get_client
    
    try:
        clickhouse_url = os.getenv('CLICKHOUSE_URL', 'http://clickhouse:8123')
        client = get_client(host=clickhouse_url.replace('http://', '').split(':')[0])
        
        # Здесь будет логика обновления метрик
        # Пока заглушка
        logging.info("Metrics updated in ClickHouse")
        
    except Exception as e:
        logging.error(f"Failed to update metrics: {e}")
        raise e

# Создание DAG
with DAG(
    dag_id=dag_id,
    default_args=default_args,
    description='Document ingestion pipeline for RAG platform',
    schedule_interval=schedule_interval,
    catchup=catchup,
    tags=['rag', 'documents', 'ingestion'],
) as dag:
    
    # Task 1: Обнаружение новых документов
    discover_task = PythonOperator(
        task_id='discover_documents',
        python_callable=discover_new_documents,
        provide_context=True,
    )
    
    # Task 2: Обработка всех документов
    process_task = PythonOperator(
        task_id='process_documents',
        python_callable=process_all_documents,
        provide_context=True,
    )
    
    # Task 3: Обновление метрик
    metrics_task = PythonOperator(
        task_id='update_metrics',
        python_callable=update_metrics,
        provide_context=True,
    )
    
    # Task 4: Очистка временных файлов
    cleanup_task = BashOperator(
        task_id='cleanup_temp_files',
        bash_command='find /tmp -name "rag_*" -mtime +1 -delete || true',
    )
    
    # Определение порядка выполнения
    discover_task >> process_task >> metrics_task >> cleanup_task
