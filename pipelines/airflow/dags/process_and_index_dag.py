"""
DAG для обработки и индексации документов
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
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
    'catchup': False
}

# Создаем DAG
dag = DAG(
    'process_and_index_documents',
    default_args=default_args,
    description='Обработка и индексация документов в RAG системе',
    schedule_interval='0 */1 * * *',  # Каждый час
    max_active_runs=1,
    tags=['rag', 'documents', 'processing', 'indexing']
)

def get_pending_documents(**context):
    """Получает документы, ожидающие обработки"""
    try:
        # В реальной реализации здесь будет запрос к БД
        # Пока используем простой файл
        pending_file = "/opt/airflow/pending_documents.json"
        
        if os.path.exists(pending_file):
            with open(pending_file, 'r') as f:
                data = json.load(f)
                pending_docs = data.get('pending_documents', [])
        else:
            pending_docs = []
        
        # Фильтруем документы по статусу
        ready_docs = [doc for doc in pending_docs if doc.get('status') == 'ready']
        
        # Сохраняем в XCom
        context['task_instance'].xcom_push(key='ready_documents', value=ready_docs)
        
        logger.info(f"Found {len(ready_docs)} documents ready for processing")
        return ready_docs
        
    except Exception as e:
        logger.error(f"Error getting pending documents: {e}")
        raise

def parse_documents(**context):
    """Парсит документы с помощью RAG Core"""
    try:
        # Получаем готовые документы
        ready_documents = context['task_instance'].xcom_pull(key='ready_documents', task_ids='get_pending_documents')
        
        if not ready_documents:
            logger.info("No documents to parse")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.parsers.document_parser import DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        from rag_core.parsers.xlsx_parser import XLSXParser
        from rag_core.parsers.html_parser import HTMLParser
        from rag_core.parsers.eml_parser import EMLParser
        
        # Создаем registry парсеров
        registry = DocumentParserRegistry()
        registry.register(PDFParser())
        registry.register(DOCXParser())
        registry.register(XLSXParser())
        registry.register(HTMLParser())
        registry.register(EMLParser())
        
        parsed_documents = []
        
        for doc in ready_documents:
            try:
                logger.info(f"Parsing document: {doc['path']}")
                
                file_path = Path(doc['path'])
                
                # Находим подходящий парсер
                parser = registry.get_parser(file_path)
                if not parser:
                    logger.warning(f"No parser found for {file_path}")
                    doc['parse_status'] = 'error'
                    doc['error_message'] = 'No suitable parser found'
                    parsed_documents.append(doc)
                    continue
                
                # Парсим документ
                parse_result = parser.parse(file_path)
                
                # Добавляем результат парсинга
                doc['parse_result'] = parse_result
                doc['parse_status'] = 'success'
                doc['parsed_at'] = datetime.now().isoformat()
                
                parsed_documents.append(doc)
                logger.info(f"Document {file_path} parsed successfully")
                
            except Exception as e:
                logger.error(f"Error parsing document {doc['path']}: {e}")
                doc['parse_status'] = 'error'
                doc['error_message'] = str(e)
                doc['parsed_at'] = datetime.now().isoformat()
                parsed_documents.append(doc)
        
        # Сохраняем результаты парсинга
        context['task_instance'].xcom_push(key='parsed_documents', value=parsed_documents)
        
        logger.info(f"Parsed {len(parsed_documents)} documents")
        return parsed_documents
        
    except Exception as e:
        logger.error(f"Error in document parsing: {e}")
        raise

def extract_tables(**context):
    """Извлекает таблицы из документов"""
    try:
        # Получаем распарсенные документы
        parsed_documents = context['task_instance'].xcom_pull(key='parsed_documents', task_ids='parse_documents')
        
        if not parsed_documents:
            logger.info("No documents to extract tables from")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.tables.table_extractor import TableExtractor
        
        # Создаем экстрактор таблиц
        table_extractor = TableExtractor()
        
        documents_with_tables = []
        
        for doc in parsed_documents:
            if doc.get('parse_status') != 'success':
                documents_with_tables.append(doc)
                continue
            
            try:
                logger.info(f"Extracting tables from: {doc['path']}")
                
                file_path = Path(doc['path'])
                
                # Извлекаем таблицы
                if file_path.suffix.lower() == '.pdf':
                    tables = table_extractor.extract_tables_from_pdf(file_path)
                else:
                    # Для других форматов таблицы уже извлечены парсером
                    tables = doc['parse_result'].get('tables', [])
                
                # Добавляем таблицы к документу
                doc['extracted_tables'] = tables
                doc['table_count'] = len(tables)
                doc['table_extraction_status'] = 'success'
                doc['tables_extracted_at'] = datetime.now().isoformat()
                
                documents_with_tables.append(doc)
                logger.info(f"Extracted {len(tables)} tables from {file_path}")
                
            except Exception as e:
                logger.error(f"Error extracting tables from {doc['path']}: {e}")
                doc['table_extraction_status'] = 'error'
                doc['error_message'] = str(e)
                doc['tables_extracted_at'] = datetime.now().isoformat()
                documents_with_tables.append(doc)
        
        # Сохраняем результаты извлечения таблиц
        context['task_instance'].xcom_push(key='documents_with_tables', value=documents_with_tables)
        
        logger.info(f"Table extraction completed for {len(documents_with_tables)} documents")
        return documents_with_tables
        
    except Exception as e:
        logger.error(f"Error in table extraction: {e}")
        raise

def create_chunks(**context):
    """Создает чанки из документов"""
    try:
        # Получаем документы с таблицами
        documents_with_tables = context['task_instance'].xcom_pull(key='documents_with_tables', task_ids='extract_tables')
        
        if not documents_with_tables:
            logger.info("No documents to chunk")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.chunking.chunker import DocumentChunker, TextChunkingStrategy, TableChunkingStrategy, MixedChunkingStrategy
        
        # Создаем стратегии чанкинга
        text_strategy = TextChunkingStrategy(chunk_size=1000, overlap=200)
        table_strategy = TableChunkingStrategy()
        mixed_strategy = MixedChunkingStrategy(text_strategy, table_strategy)
        
        # Создаем чанкер
        chunker = DocumentChunker(mixed_strategy)
        
        documents_with_chunks = []
        
        for doc in documents_with_tables:
            if doc.get('parse_status') != 'success':
                documents_with_chunks.append(doc)
                continue
            
            try:
                logger.info(f"Creating chunks for: {doc['path']}")
                
                # Создаем чанки
                chunks = chunker.create_chunks(
                    text=doc['parse_result'].get('text', ''),
                    tables=doc.get('extracted_tables', []),
                    metadata=doc['parse_result'].get('metadata', {})
                )
                
                # Добавляем чанки к документу
                doc['chunks'] = [chunk.__dict__ for chunk in chunks]
                doc['chunk_count'] = len(chunks)
                doc['chunking_status'] = 'success'
                doc['chunked_at'] = datetime.now().isoformat()
                
                documents_with_chunks.append(doc)
                logger.info(f"Created {len(chunks)} chunks for {doc['path']}")
                
            except Exception as e:
                logger.error(f"Error creating chunks for {doc['path']}: {e}")
                doc['chunking_status'] = 'error'
                doc['error_message'] = str(e)
                doc['chunked_at'] = datetime.now().isoformat()
                documents_with_chunks.append(doc)
        
        # Сохраняем результаты чанкинга
        context['task_instance'].xcom_push(key='documents_with_chunks', value=documents_with_chunks)
        
        logger.info(f"Chunking completed for {len(documents_with_chunks)} documents")
        return documents_with_chunks
        
    except Exception as e:
        logger.error(f"Error in chunking: {e}")
        raise

def generate_embeddings(**context):
    """Генерирует эмбеддинги для чанков"""
    try:
        # Получаем документы с чанками
        documents_with_chunks = context['task_instance'].xcom_pull(key='documents_with_chunks', task_ids='create_chunks')
        
        if not documents_with_chunks:
            logger.info("No documents to generate embeddings for")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        # Создаем сервис эмбеддингов
        embedding_service = EmbeddingService()
        
        documents_with_embeddings = []
        
        for doc in documents_with_chunks:
            if doc.get('chunking_status') != 'success':
                documents_with_embeddings.append(doc)
                continue
            
            try:
                logger.info(f"Generating embeddings for: {doc['path']}")
                
                chunks = doc['chunks']
                embeddings = []
                
                # Генерируем эмбеддинги для каждого чанка
                for chunk in chunks:
                    if chunk.get('text'):
                        # Генерируем эмбеддинг для текста
                        embedding = embedding_service.get_embedding(chunk['text'])
                        embeddings.append(embedding)
                    else:
                        # Для таблиц используем нулевой вектор (заглушка)
                        embedding = [0.0] * 1024
                        embeddings.append(embedding)
                
                # Добавляем эмбеддинги к документу
                doc['embeddings'] = embeddings
                doc['embedding_count'] = len(embeddings)
                doc['embedding_status'] = 'success'
                doc['embeddings_generated_at'] = datetime.now().isoformat()
                
                documents_with_embeddings.append(doc)
                logger.info(f"Generated {len(embeddings)} embeddings for {doc['path']}")
                
            except Exception as e:
                logger.error(f"Error generating embeddings for {doc['path']}: {e}")
                doc['embedding_status'] = 'error'
                doc['error_message'] = str(e)
                doc['embeddings_generated_at'] = datetime.now().isoformat()
                documents_with_embeddings.append(doc)
        
        # Сохраняем результаты генерации эмбеддингов
        context['task_instance'].xcom_push(key='documents_with_embeddings', value=documents_with_embeddings)
        
        logger.info(f"Embedding generation completed for {len(documents_with_embeddings)} documents")
        return documents_with_embeddings
        
    except Exception as e:
        logger.error(f"Error in embedding generation: {e}")
        raise

def index_to_vectorstore(**context):
    """Индексирует документы в векторное хранилище"""
    try:
        # Получаем документы с эмбеддингами
        documents_with_embeddings = context['task_instance'].xcom_pull(key='documents_with_embeddings', task_ids='generate_embeddings')
        
        if not documents_with_embeddings:
            logger.info("No documents to index")
            return []
        
        # Импортируем RAG Core
        import sys
        sys.path.append('/opt/airflow/rag_core')
        
        from rag_core.vectorstore.pgvector_store import PgVectorStore
        
        # Получаем конфигурацию
        pg_dsn = Variable.get("pg_dsn", default_var="postgresql://postgres:postgres@postgres:5432/rag_app")
        
        # Создаем векторное хранилище
        vector_store = PgVectorStore(pg_dsn)
        
        indexed_documents = []
        
        for doc in documents_with_embeddings:
            if doc.get('embedding_status') != 'success':
                indexed_documents.append(doc)
                continue
            
            try:
                logger.info(f"Indexing document: {doc['path']}")
                
                file_path = Path(doc['path'])
                
                # Создаем документ в БД
                doc_id = vector_store.ensure_document(
                    source_path=str(file_path),
                    sha256=doc.get('hash', ''),
                    title=doc['parse_result'].get('title', file_path.name),
                    mime_type=doc.get('mime_type'),
                    size_bytes=doc.get('size', 0),
                    metadata=doc['parse_result'].get('metadata', {})
                )
                
                # Подготавливаем данные чанков
                chunks_data = []
                for chunk in doc['chunks']:
                    chunk_data = {
                        'chunk_index': chunk.get('chunk_index', 0),
                        'chunk_type': chunk.get('chunk_type', 'text'),
                        'content': chunk.get('text', ''),
                        'table_html': chunk.get('table_html'),
                        'bbox': chunk.get('bbox'),
                        'page_no': chunk.get('page_no'),
                        'metadata': chunk.get('metadata', {})
                    }
                    chunks_data.append(chunk_data)
                
                # Сохраняем чанки и эмбеддинги
                chunk_ids = vector_store.upsert_chunks_and_embeddings(
                    doc_id=doc_id,
                    chunks=chunks_data,
                    embeddings=doc['embeddings']
                )
                
                # Добавляем информацию об индексации
                doc['doc_id'] = doc_id
                doc['chunk_ids'] = chunk_ids
                doc['indexing_status'] = 'success'
                doc['indexed_at'] = datetime.now().isoformat()
                
                indexed_documents.append(doc)
                logger.info(f"Indexed document {file_path} with {len(chunk_ids)} chunks")
                
            except Exception as e:
                logger.error(f"Error indexing document {doc['path']}: {e}")
                doc['indexing_status'] = 'error'
                doc['error_message'] = str(e)
                doc['indexed_at'] = datetime.now().isoformat()
                indexed_documents.append(doc)
        
        # Сохраняем результаты индексации
        context['task_instance'].xcom_push(key='indexed_documents', value=indexed_documents)
        
        logger.info(f"Indexing completed for {len(indexed_documents)} documents")
        return indexed_documents
        
    except Exception as e:
        logger.error(f"Error in indexing: {e}")
        raise

def update_processing_status(**context):
    """Обновляет статус обработки документов"""
    try:
        # Получаем проиндексированные документы
        indexed_documents = context['task_instance'].xcom_pull(key='indexed_documents', task_ids='index_to_vectorstore')
        
        if not indexed_documents:
            logger.info("No documents to update status")
            return
        
        # В реальной реализации здесь будет обновление БД
        # Пока просто логируем
        
        success_count = sum(1 for doc in indexed_documents if doc.get('indexing_status') == 'success')
        error_count = sum(1 for doc in indexed_documents if doc.get('indexing_status') == 'error')
        
        logger.info(f"Processing completed: {success_count} success, {error_count} errors")
        
        # Обновляем статус документов
        update_document_status(indexed_documents)
        
    except Exception as e:
        logger.error(f"Error updating processing status: {e}")
        raise

def update_document_status(documents):
    """Обновляет статус документов"""
    try:
        # В реальной реализации здесь будет обновление БД
        # Пока просто логируем
        
        for doc in documents:
            if doc.get('indexing_status') == 'success':
                logger.info(f"Document {doc['path']} successfully processed and indexed")
            else:
                logger.error(f"Document {doc['path']} failed: {doc.get('error_message', 'Unknown error')}")
        
        logger.info(f"Status updated for {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Error updating document status: {e}")

def generate_processing_report(**context):
    """Генерирует отчет об обработке"""
    try:
        # Получаем все данные
        ready_documents = context['task_instance'].xcom_pull(key='ready_documents', task_ids='get_pending_documents')
        parsed_documents = context['task_instance'].xcom_pull(key='parsed_documents', task_ids='parse_documents')
        documents_with_tables = context['task_instance'].xcom_pull(key='documents_with_tables', task_ids='extract_tables')
        documents_with_chunks = context['task_instance'].xcom_pull(key='documents_with_chunks', task_ids='create_chunks')
        documents_with_embeddings = context['task_instance'].xcom_pull(key='documents_with_embeddings', task_ids='generate_embeddings')
        indexed_documents = context['task_instance'].xcom_pull(key='indexed_documents', task_ids='index_to_vectorstore')
        
        # Формируем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'ready_documents': len(ready_documents) if ready_documents else 0,
            'parsing': {
                'total': len(parsed_documents) if parsed_documents else 0,
                'success': sum(1 for doc in parsed_documents if doc and doc.get('parse_status') == 'success') if parsed_documents else 0,
                'errors': sum(1 for doc in parsed_documents if doc and doc.get('parse_status') == 'error') if parsed_documents else 0
            },
            'table_extraction': {
                'total': len(documents_with_tables) if documents_with_tables else 0,
                'success': sum(1 for doc in documents_with_tables if doc and doc.get('table_extraction_status') == 'success') if documents_with_tables else 0,
                'errors': sum(1 for doc in documents_with_tables if doc and doc.get('table_extraction_status') == 'error') if documents_with_tables else 0
            },
            'chunking': {
                'total': len(documents_with_chunks) if documents_with_chunks else 0,
                'success': sum(1 for doc in documents_with_chunks if doc and doc.get('chunking_status') == 'success') if documents_with_chunks else 0,
                'errors': sum(1 for doc in documents_with_chunks if doc and doc.get('chunking_status') == 'error') if documents_with_chunks else 0
            },
            'embedding_generation': {
                'total': len(documents_with_embeddings) if documents_with_embeddings else 0,
                'success': sum(1 for doc in documents_with_embeddings if doc and doc.get('embedding_status') == 'success') if documents_with_embeddings else 0,
                'errors': sum(1 for doc in documents_with_embeddings if doc and doc.get('embedding_status') == 'error') if documents_with_embeddings else 0
            },
            'indexing': {
                'total': len(indexed_documents) if indexed_documents else 0,
                'success': sum(1 for doc in indexed_documents if doc and doc.get('indexing_status') == 'success') if indexed_documents else 0,
                'errors': sum(1 for doc in indexed_documents if doc and doc.get('indexing_status') == 'error') if indexed_documents else 0
            }
        }
        
        # Сохраняем отчет
        context['task_instance'].xcom_push(key='processing_report', value=report)
        
        # Логируем отчет
        logger.info("Processing Report:")
        logger.info(f"  Ready documents: {report['ready_documents']}")
        logger.info(f"  Parsing: {report['parsing']['success']}/{report['parsing']['total']} success")
        logger.info(f"  Table extraction: {report['table_extraction']['success']}/{report['table_extraction']['total']} success")
        logger.info(f"  Chunking: {report['chunking']['success']}/{report['chunking']['total']} success")
        logger.info(f"  Embedding generation: {report['embedding_generation']['success']}/{report['embedding_generation']['total']} success")
        logger.info(f"  Indexing: {report['indexing']['success']}/{report['indexing']['total']} success")
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

# Определяем задачи
start_task = EmptyOperator(task_id='start', dag=dag)

get_pending_task = PythonOperator(
    task_id='get_pending_documents',
    python_callable=get_pending_documents,
    dag=dag
)

parse_task = PythonOperator(
    task_id='parse_documents',
    python_callable=parse_documents,
    dag=dag
)

extract_tables_task = PythonOperator(
    task_id='extract_tables',
    python_callable=extract_tables,
    dag=dag
)

chunk_task = PythonOperator(
    task_id='create_chunks',
    python_callable=create_chunks,
    dag=dag
)

embedding_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    dag=dag
)

index_task = PythonOperator(
    task_id='index_to_vectorstore',
    python_callable=index_to_vectorstore,
    dag=dag
)

update_status_task = PythonOperator(
    task_id='update_processing_status',
    python_callable=update_processing_status,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_processing_report,
    dag=dag
)

end_task = EmptyOperator(task_id='end', dag=dag)

# Определяем зависимости
start_task >> get_pending_task >> parse_task >> extract_tables_task >> chunk_task >> embedding_task >> index_task >> update_status_task >> report_task >> end_task
