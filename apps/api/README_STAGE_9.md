# Этап 9: API - Расширенная функциональность ✅ ЗАВЕРШЕН

## Обзор

Этап 9 добавляет расширенную функциональность к API RAG Platform, включая:

- 🔐 **Система ролей и ACL** - управление пользователями, ролями и правами доступа
- 🔍 **Фильтрация по метаданным** - поиск с учетом ACL и метаданных документов
- 📄 **Пагинация результатов** - постраничный вывод для больших объемов данных
- 💾 **Кэширование запросов** - Redis для ускорения работы API
- ⏱️ **Rate limiting** - защита от злоупотреблений и DDoS атак

## Архитектура

### Компоненты

```
src/
├── schemas/
│   └── auth.py              # Схемы аутентификации и авторизации
├── services/
│   ├── auth.py              # Сервис JWT токенов и проверки прав
│   └── cache.py             # Сервис кэширования Redis
├── middleware/
│   ├── auth.py              # Middleware аутентификации
│   └── rate_limit.py        # Middleware rate limiting
└── routers/
    └── auth.py              # Роутер аутентификации
```

### Схемы данных

#### Пользователи и роли

```python
class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    tenant_id: int
    role_id: int
    is_active: bool

class Role(BaseModel):
    id: int
    name: str
    tenant_id: int
    permissions: List[Permission]
    is_active: bool

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"
```

#### ACL для документов

```python
class DocumentACL(BaseModel):
    id: int
    document_id: int
    tenant_id: int
    role_id: Optional[int]
    user_id: Optional[int]
    permissions: List[Permission]
    created_at: datetime
    created_by: int
```

### JWT Токены

- **Access Token**: 30 минут, для доступа к API
- **Refresh Token**: 7 дней, для обновления access token
- Алгоритм: HS256
- Поддержка ролей и разрешений в payload

### Кэширование

- **Redis** как основное хранилище кэша
- Поддержка JSON и pickle сериализации
- TTL для автоматического истечения
- Паттерны для массовых операций

### Rate Limiting

- **По минутам**: 60 запросов
- **По часам**: 1000 запросов  
- **По дням**: 10000 запросов
- **Burst limit**: 10 запросов подряд
- Идентификация по API ключу, JWT токену или IP адресу

## API Эндпоинты

### Аутентификация

```
POST /api/v1/auth/login          # Вход в систему
POST /api/v1/auth/refresh        # Обновление токена
GET  /api/v1/auth/me            # Информация о текущем пользователе
```

### Управление пользователями (Admin)

```
POST   /api/v1/auth/users       # Создание пользователя
GET    /api/v1/auth/users       # Список пользователей
GET    /api/v1/auth/users/{id}  # Информация о пользователе
PUT    /api/v1/auth/users/{id}  # Обновление пользователя
```

### Роли и тенанты

```
GET /api/v1/auth/roles          # Список ролей
GET /api/v1/auth/tenants        # Список тенантов
```

## Использование

### 1. Вход в систему

```python
import requests

# Вход
response = requests.post("http://localhost:8080/api/v1/auth/login", json={
    "username": "admin",
    "password": "admin123"
})

tokens = response.json()
access_token = tokens["access_token"]
```

### 2. Использование защищенных эндпоинтов

```python
headers = {"Authorization": f"Bearer {access_token}"}

# Получение информации о пользователе
response = requests.get(
    "http://localhost:8080/api/v1/auth/me",
    headers=headers
)

user_info = response.json()
```

### 3. Создание пользователя (Admin)

```python
user_data = {
    "username": "new_user",
    "email": "user@example.com",
    "password": "secure_password",
    "tenant_id": 1,
    "role_id": 2
}

response = requests.post(
    "http://localhost:8080/api/v1/auth/users",
    json=user_data,
    headers=headers
)
```

### 4. Работа с кэшем

```python
from src.services.cache import cache_service

# Установка значения
await cache_service.set("user:123", user_data, ttl=3600)

# Получение значения
user_data = await cache_service.get("user:123")

# Удаление
await cache_service.delete("user:123")
```

### 5. Rate Limiting

```python
from src.middleware.rate_limit import rate_limit

@router.post("/api/v1/endpoint")
@rate_limit(requests_per_minute=30, burst_limit=5)
async def endpoint():
    # Эндпоинт с ограничением 30 запросов в минуту
    pass
```

## Безопасность

### JWT Токены

- Секретный ключ из переменных окружения
- Проверка типа токена (access/refresh)
- Автоматическое истечение
- Безопасное хранение в заголовках

### Пароли

- Хеширование с bcrypt
- Минимальная длина: 8 символов
- Проверка сложности (опционально)

### ACL

- Проверка на уровне тенанта
- Ролевая модель доступа
- Фильтрация результатов по правам
- Аудит действий пользователей

### Rate Limiting

- Защита от DDoS атак
- Настраиваемые лимиты
- Идентификация по различным параметрам
- Graceful degradation при превышении лимитов

## Конфигурация

### Переменные окружения

```bash
# JWT
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=

# CORS
CORS_ORIGINS=["*"]
ALLOWED_HOSTS=["*"]
```

### Настройки по умолчанию

```python
# Rate Limiting
requests_per_minute: 60
requests_per_hour: 1000
requests_per_day: 10000
burst_limit: 10

# Кэширование
default_ttl: 3600  # 1 час
```

## Тестирование

### Запуск тестов

```bash
cd apps/api
python -m pytest test_auth.py -v
```

### Примеры использования

```bash
python examples/auth_examples.py
```

### Тестовые учетные данные

```
Admin:
- username: admin
- password: admin123
- permissions: [ADMIN]

User:
- username: user  
- password: user123
- permissions: [READ, WRITE]
```

## Мониторинг

### Логирование

- Вход/выход пользователей
- Создание/обновление пользователей
- Нарушения безопасности
- Rate limiting события

### Метрики

- Количество активных пользователей
- Частота запросов по эндпоинтам
- Использование кэша
- Время ответа API

### Алерты

- Превышение rate limit
- Неудачные попытки входа
- Подозрительная активность
- Проблемы с Redis

## Следующие шаги

### Этап 10: Streamlit Frontend

- Создание веб-интерфейса
- Интеграция с API аутентификации
- Управление сессиями пользователей
- Адаптивный дизайн

### Улучшения безопасности

- 2FA аутентификация
- OAuth интеграция
- Аудит действий
- Шифрование данных

### Производительность

- Оптимизация запросов к БД
- Кэширование стратегий
- Балансировка нагрузки
- Мониторинг производительности

## Заключение

Этап 9 успешно реализован и добавляет:

✅ **Система ролей и ACL** - полное управление доступом  
✅ **Фильтрация по метаданным** - безопасный поиск документов  
✅ **Пагинация результатов** - эффективная работа с большими объемами  
✅ **Кэширование запросов** - Redis для ускорения API  
✅ **Rate limiting** - защита от злоупотреблений  

API готов к продакшн использованию с полной системой безопасности и авторизации.
