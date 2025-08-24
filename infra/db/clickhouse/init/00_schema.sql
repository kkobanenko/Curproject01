-- Создаем базу данных
CREATE DATABASE IF NOT EXISTS rag;

-- Таблица для метрик документов
CREATE TABLE IF NOT EXISTS rag.document_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    doc_id String,
    doc_type String,
    processing_time_ms UInt32,
    chunk_count UInt32,
    embedding_count UInt32,
    file_size_bytes UInt64,
    success Boolean
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, doc_id);

-- Таблица для метрик поиска
CREATE TABLE IF NOT EXISTS rag.search_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    query_hash String,
    query_length UInt32,
    result_count UInt32,
    response_time_ms UInt32,
    success Boolean
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, query_hash);

-- Таблица для метрик чата
CREATE TABLE IF NOT EXISTS rag.chat_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    session_id String,
    message_count UInt32,
    total_tokens UInt32,
    response_time_ms UInt32,
    success Boolean
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, session_id);

-- Таблица для логов ошибок
CREATE TABLE IF NOT EXISTS rag.error_logs (
    timestamp DateTime64(3),
    tenant_id String,
    service String,
    error_type String,
    error_message String,
    stack_trace String
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, service);
