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

-- Таблица для метрик производительности системы
CREATE TABLE IF NOT EXISTS rag.system_metrics (
    timestamp DateTime64(3),
    service String,
    metric_name String,
    metric_value Float64,
    metric_unit String,
    tags Map(String, String)
) ENGINE = MergeTree()
ORDER BY (timestamp, service, metric_name);

-- Таблица для метрик качества поиска
CREATE TABLE IF NOT EXISTS rag.search_quality_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    query_id String,
    query_text String,
    relevance_score Float64,
    precision_score Float64,
    recall_score Float64,
    f1_score Float64,
    user_feedback String,
    response_quality Float64
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, query_id);

-- Таблица для метрик использования ресурсов
CREATE TABLE IF NOT EXISTS rag.resource_usage_metrics (
    timestamp DateTime64(3),
    service String,
    cpu_usage_percent Float64,
    memory_usage_mb UInt64,
    disk_usage_mb UInt64,
    network_io_bytes UInt64,
    active_connections UInt32,
    queue_length UInt32
) ENGINE = MergeTree()
ORDER BY (timestamp, service);

-- Таблица для метрик пользовательской активности
CREATE TABLE IF NOT EXISTS rag.user_activity_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    user_id String,
    session_id String,
    action_type String,
    action_duration_ms UInt32,
    success Boolean,
    metadata Map(String, String)
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, user_id);

-- Таблица для алертов
CREATE TABLE IF NOT EXISTS rag.alerts (
    timestamp DateTime64(3),
    alert_id String,
    alert_type String,
    severity String,
    service String,
    message String,
    status String,
    resolved_at Nullable(DateTime64(3)),
    metadata Map(String, String)
) ENGINE = MergeTree()
ORDER BY (timestamp, alert_id);

-- Таблица для метрик API
CREATE TABLE IF NOT EXISTS rag.api_metrics (
    timestamp DateTime64(3),
    endpoint String,
    method String,
    status_code UInt16,
    response_time_ms UInt32,
    request_size_bytes UInt32,
    response_size_bytes UInt32,
    user_id String,
    tenant_id String
) ENGINE = MergeTree()
ORDER BY (timestamp, endpoint, method);

-- Таблица для метрик эмбеддингов
CREATE TABLE IF NOT EXISTS rag.embedding_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    model_name String,
    embedding_dimension UInt32,
    processing_time_ms UInt32,
    tokens_processed UInt32,
    success Boolean,
    error_message Nullable(String)
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, model_name);

-- Таблица для метрик векторного поиска
CREATE TABLE IF NOT EXISTS rag.vector_search_metrics (
    timestamp DateTime64(3),
    tenant_id String,
    query_vector_dimension UInt32,
    search_time_ms UInt32,
    results_count UInt32,
    index_type String,
    similarity_threshold Float64,
    success Boolean
) ENGINE = MergeTree()
ORDER BY (timestamp, tenant_id, index_type);

-- Создаем материализованные представления для агрегации метрик
CREATE MATERIALIZED VIEW IF NOT EXISTS rag.hourly_system_metrics
ENGINE = SummingMergeTree()
ORDER BY (hour, service, metric_name)
AS SELECT
    toStartOfHour(timestamp) as hour,
    service,
    metric_name,
    avg(metric_value) as avg_value,
    max(metric_value) as max_value,
    min(metric_value) as min_value,
    count() as sample_count
FROM rag.system_metrics
GROUP BY hour, service, metric_name;

-- Материализованное представление для ежедневной статистики поиска
CREATE MATERIALIZED VIEW IF NOT EXISTS rag.daily_search_stats
ENGINE = SummingMergeTree()
ORDER BY (date, tenant_id)
AS SELECT
    toDate(timestamp) as date,
    tenant_id,
    count() as total_searches,
    avg(response_time_ms) as avg_response_time,
    countIf(success = 1) as successful_searches,
    countIf(success = 0) as failed_searches
FROM rag.search_metrics
GROUP BY date, tenant_id;

-- Материализованное представление для статистики ошибок
CREATE MATERIALIZED VIEW IF NOT EXISTS rag.daily_error_stats
ENGINE = SummingMergeTree()
ORDER BY (date, tenant_id, service)
AS SELECT
    toDate(timestamp) as date,
    tenant_id,
    service,
    count() as error_count,
    uniqExact(error_type) as unique_error_types
FROM rag.error_logs
GROUP BY date, tenant_id, service;

-- Создаем индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_system_metrics_service ON rag.system_metrics (service) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_search_metrics_tenant ON rag.search_metrics (tenant_id) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_error_logs_service ON rag.error_logs (service) TYPE set(0) GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON rag.api_metrics (endpoint) TYPE set(0) GRANULARITY 1;
