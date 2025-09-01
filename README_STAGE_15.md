# Этап 15: Интеграция с внешними системами

## 🔗 Обзор

Этап 15 добавляет мощные возможности интеграции RAG платформы с внешними системами, включая webhook уведомления, REST API для CRM/ERP, экспорт данных и синхронизацию с внешними базами данных.

## ✅ Реализованные возможности

### 1. 🔔 Система Webhooks

#### Типы событий
```python
class WebhookEventType(str, Enum):
    # Документы
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed" 
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_SHARED = "document.shared"
    
    # Пользователи
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    # RAG операции
    RAG_QUERY_COMPLETED = "rag.query.completed"
    SEARCH_PERFORMED = "search.performed"
    
    # Система
    SYSTEM_ALERT = "system.alert"
    SECURITY_VIOLATION = "security.violation"
    
    # Кастомные события
    CUSTOM_EVENT = "custom.event"
```

#### Возможности webhooks
- **Надежная доставка** с автоматическими повторными попытками
- **Подпись HMAC** для проверки подлинности
- **Фильтрация событий** по тенантам и содержимому
- **Rate limiting** для защиты внешних систем
- **Статистика доставки** и мониторинг
- **Тестирование** webhook endpoints

#### Пример использования
```python
# Регистрация webhook
webhook = WebhookEndpoint(
    name="CRM Integration",
    url="https://crm.company.com/webhooks/rag-platform",
    events=[
        WebhookEventType.DOCUMENT_UPLOADED,
        WebhookEventType.RAG_QUERY_COMPLETED
    ],
    secret_token="secure-secret-key",
    timeout_seconds=30,
    max_retries=3
)

# Автоматическая отправка событий
await event_triggers.document_uploaded(
    document_id="doc123",
    filename="contract.pdf",
    content_type="application/pdf",
    size_bytes=1024000,
    user_context=current_user
)
```

### 2. 🌐 REST API для внешних интеграций

#### CRM Коннектор
```python
class CRMConnector(BaseAPIConnector):
    """Интеграция с CRM системами"""
    
    # Поддерживаемые типы аутентификации
    - API Key
    - OAuth 2.0
    - Basic Auth
    
    # Операции
    - Создание/обновление контактов
    - Синхронизация данных пользователей
    - Получение информации о клиентах
```

#### ERP Коннектор
```python
class ERPConnector(BaseAPIConnector):
    """Интеграция с ERP системами"""
    
    # Специализированные операции
    - Создание счетов (invoices)
    - Обновление складских остатков
    - Получение заказов
    - Синхронизация продуктов
```

#### Маппинг полей
```python
# Конфигурация маппинга полей
field_mapping = {
    "username": "contact_name",
    "email": "contact_email", 
    "phone": "contact_phone",
    "company": "account_name"
}
```

#### Rate Limiting
- Автоматическое ограничение запросов к внешним API
- Конфигурируемые лимиты (запросов в минуту)
- Умная очередь с задержками

### 3. 📤 Экспорт данных

#### Поддерживаемые форматы
- **JSON** - структурированные данные
- **CSV** - табличные данные
- **XML** - иерархические данные  
- **Excel** - с метаданными и форматированием
- **YAML** - конфигурационные данные
- **ZIP** - сжатие больших файлов

#### Типы экспорта
```python
export_types = [
    "documents",      # Документы с метаданными
    "users",         # Пользователи и роли
    "search_queries", # История поисковых запросов
    "audit_logs"     # Логи аудита
]
```

#### Фильтры экспорта
```python
export_request = DataExportRequest(
    export_type="documents",
    format="excel",
    date_from=datetime(2024, 1, 1),
    date_to=datetime(2024, 12, 31),
    tenant_id=123,
    document_types=["application/pdf"],
    include_content=True,
    include_metadata=True,
    compress=True,
    max_records=10000
)
```

#### Асинхронная обработка
- Задачи экспорта выполняются в фоне
- Отслеживание прогресса в реальном времени
- Уведомления через webhooks о завершении
- Автоматическая очистка просроченных файлов

### 4. 🔄 Синхронизация баз данных

#### Направления синхронизации
- **Import** - импорт данных в RAG платформу
- **Export** - экспорт данных во внешние системы
- **Bidirectional** - двусторонняя синхронизация

#### Поддерживаемые БД
- PostgreSQL
- MySQL
- SQL Server
- Oracle
- SQLite

#### Конфигурация синхронизации
```python
sync_config = DatabaseSync(
    name="CRM Users Sync",
    source_type="postgresql",
    connection_string="postgresql://user:pass@host:5432/db",
    sync_direction="bidirectional",
    schedule="0 */6 * * *",  # Каждые 6 часов
    table_mappings=[
        {
            "source_table": "crm_contacts",
            "target_table": "users",
            "field_mapping": {
                "contact_name": "username",
                "contact_email": "email"
            }
        }
    ],
    conflict_resolution="source_wins"
)
```

### 5. 📚 Автоматическая API документация

#### Расширенное описание API
- Детальное описание всех эндпоинтов
- Примеры запросов и ответов
- Информация об аутентификации
- Rate limiting правила
- Коды ошибок с описаниями

#### Интерактивная документация
- **Swagger UI** на `/docs`
- **ReDoc** на `/redoc` 
- Возможность тестирования API прямо в документации
- Автоматическая генерация схем

#### Метаданные API
```python
app = FastAPI(
    title="RAG Platform API",
    description="Полнофункциональная система для работы с документами...",
    version="1.0.0",
    contact={
        "name": "RAG Platform Support",
        "email": "support@rag-platform.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)
```

## 🏗️ Архитектура интеграций

### Схема компонентов
```
📁 apps/api/src/
├── 🔗 services/
│   ├── webhook_service.py     # Система webhooks
│   ├── external_api.py        # Интеграция с внешними API
│   ├── data_export.py         # Экспорт данных
│   └── database_sync.py       # Синхронизация БД
├── 📋 schemas/
│   └── webhooks.py           # Схемы для интеграций
└── 🌐 routers/
    └── webhooks.py           # API эндпоинты
```

### Поток данных

```mermaid
graph TB
    A[RAG Platform] --> B[Webhook Service]
    B --> C[External Systems]
    
    D[External API] --> E[CRM Connector]
    D --> F[ERP Connector]
    E --> G[CRM System]
    F --> H[ERP System]
    
    I[Data Export] --> J[JSON/CSV/Excel]
    I --> K[Compressed Files]
    
    L[Database Sync] --> M[External Database]
    M --> L
```

## 🔧 Конфигурация и использование

### Переменные окружения
```bash
# Webhook настройки
WEBHOOK_DELIVERY_TIMEOUT=30
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_DELAY=60

# Экспорт
EXPORT_DIR=/tmp/exports
EXPORT_MAX_FILE_SIZE=100MB
EXPORT_RETENTION_HOURS=24

# Внешние API
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_RATE_LIMIT=100

# Синхронизация БД
DB_SYNC_BATCH_SIZE=1000
DB_SYNC_TIMEOUT=300
```

### Зависимости
```requirements.txt
# Экспорт данных
pandas>=2.0.0
openpyxl>=3.1.0
PyYAML>=6.0

# HTTP клиент для интеграций
httpx>=0.25.0
```

## 📊 API Эндпоинты

### Webhooks
```http
POST   /webhooks              # Создание webhook
GET    /webhooks              # Список webhooks
GET    /webhooks/{id}         # Получение webhook
PUT    /webhooks/{id}         # Обновление webhook
DELETE /webhooks/{id}         # Удаление webhook
GET    /webhooks/{id}/stats   # Статистика webhook
POST   /webhooks/{id}/test    # Тестирование webhook
POST   /webhooks/trigger-event # Ручной trigger события
```

### Экспорт данных
```http
POST   /webhooks/export       # Создание задачи экспорта
GET    /webhooks/export/{id}  # Статус задачи экспорта
GET    /export/{id}/download  # Скачивание файла
```

### Внешние API
```http
POST   /integrations/apis     # Регистрация внешнего API
GET    /integrations/apis     # Список API
POST   /integrations/sync     # Синхронизация данных
GET    /integrations/status   # Статус интеграций
```

## 🚀 Примеры использования

### Создание webhook для CRM
```python
import httpx

# Создание webhook
webhook_data = {
    "name": "CRM Customer Updates",
    "url": "https://crm.company.com/webhooks/rag",
    "events": [
        "user.registered",
        "document.uploaded"
    ],
    "secret_token": "crm-webhook-secret",
    "active": True,
    "content_filter": {
        "tenant_id": 123
    }
}

response = httpx.post(
    "http://localhost:8081/webhooks/",
    json=webhook_data,
    headers={"Authorization": "Bearer <token>"}
)
```

### Интеграция с ERP
```python
# Конфигурация ERP API
erp_config = {
    "name": "Company ERP",
    "base_url": "https://erp.company.com/api",
    "api_type": "rest",
    "auth_type": "oauth2",
    "auth_config": {
        "client_id": "rag-platform",
        "client_secret": "secret",
        "token_url": "https://erp.company.com/oauth/token"
    },
    "field_mapping": {
        "document_id": "external_doc_id",
        "title": "document_name"
    }
}

# Синхронизация данных документа
sync_result = await external_api_service.sync_document_data(
    api_id=erp_api_id,
    document_data={
        "id": "doc123",
        "title": "Contract Agreement",
        "content_type": "application/pdf",
        "created_at": "2024-01-01T00:00:00Z"
    },
    user_context=current_user
)
```

### Экспорт данных в Excel
```python
# Создание задачи экспорта
export_request = {
    "export_type": "documents",
    "format": "excel",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-12-31T23:59:59Z",
    "include_content": False,
    "include_metadata": True,
    "compress": True,
    "max_records": 5000
}

response = httpx.post(
    "http://localhost:8081/webhooks/export",
    json=export_request,
    headers={"Authorization": "Bearer <token>"}
)

job_id = response.json()["id"]

# Проверка статуса
status_response = httpx.get(
    f"http://localhost:8081/webhooks/export/{job_id}",
    headers={"Authorization": "Bearer <token>"}
)

if status_response.json()["status"] == "completed":
    # Скачивание файла
    download_url = status_response.json()["download_url"]
    file_response = httpx.get(download_url)
```

## 🔍 Мониторинг и логирование

### Метрики интеграций
- Количество отправленных webhooks
- Успешность доставки webhooks
- Время ответа внешних API
- Объем экспортированных данных
- Ошибки синхронизации

### Аудит интеграций
```python
# Автоматический аудит всех операций
AuditService.log_action(
    action=AuditAction.EXPORT_DATA,
    level=AuditLevel.INFO,
    user_context=user_context,
    resource_type="export_job",
    resource_id=job_id,
    details={
        "export_type": "documents",
        "format": "excel",
        "records_count": 1000
    }
)
```

### Алерты
- Неудачные доставки webhooks
- Недоступность внешних API
- Превышение лимитов экспорта
- Ошибки синхронизации БД

## 🛡️ Безопасность интеграций

### Аутентификация внешних систем
- API ключи с ограниченными правами
- OAuth 2.0 для доверенных систем
- Подписи HMAC для webhooks
- IP whitelist для критичных интеграций

### Защита данных
- Шифрование конфигураций API
- Маскирование чувствительных данных в логах
- Ограничение объема экспортируемых данных
- Автоматическая очистка временных файлов

### Валидация данных
- Проверка схем входящих данных
- Санитизация полей перед экспортом
- Контроль размера файлов
- Проверка типов MIME

## 📈 Производительность

### Оптимизации
- Асинхронная обработка webhooks
- Пакетная синхронизация данных
- Кэширование результатов API
- Сжатие экспортируемых файлов

### Ограничения
- Rate limiting для внешних API
- Лимиты размера экспорта
- Таймауты для webhook доставки
- Очереди для обработки событий

## 🔮 Планы развития

### Дополнительные интеграции
- Slack/Teams уведомления
- Google Drive/Dropbox синхронизация
- Zapier/Microsoft Power Automate
- GraphQL API поддержка

### Улучшения экспорта
- Streaming экспорт больших данных
- Инкрементальный экспорт изменений
- Кастомные шаблоны экспорта
- Автоматические расписания экспорта

### Расширенные webhooks
- Webhooks с фильтрацией по ML
- Batch webhooks для группировки событий
- Webhook трансформации данных
- Webhook цепочки (chaining)

## 🏆 Заключение

Этап 15 превращает RAG платформу в полноценную интеграционную платформу:

✅ **Система webhooks** для real-time уведомлений  
✅ **REST API интеграции** с CRM/ERP системами  
✅ **Мощный экспорт данных** в 5+ форматах  
✅ **Синхронизация БД** в реальном времени  
✅ **Автоматическая документация** API  
✅ **Enterprise-ready интеграции** с аудитом и безопасностью  

Платформа теперь может легко интегрироваться с любыми внешними системами и обеспечивать бесшовный обмен данными.

Переходим к **Этапу 16: Оптимизация и производительность** 🚀
