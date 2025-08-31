"""
Конфигурация Superset для RAG-платформы (версия 5.0.0)
"""
import os
from datetime import timedelta

# Базовая конфигурация
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'CHANGE_ME_SUPERSET_SECRET')

# База данных метаданных
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'SUPERSET_DATABASE_URI',
    'postgresql+psycopg2://postgres:postgres@postgres:5432/superset'
)

# Настройки безопасности
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Настройки сессий
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # В продакшене True
SESSION_COOKIE_SAMESITE = 'Lax'

# Настройки кэширования
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Настройки безопасности
ENABLE_PROXY_FIX = True
PROXY_FIX_CONFIG = {
    "x_for": 1,
    "x_proto": 1,
    "x_host": 1,
    "x_port": 1,
    "x_prefix": 1,
}

# Настройки логирования
ENABLE_TIME_ROTATE = True
TIME_ROTATE_LOG_LEVEL = 'INFO'

# Настройки функций
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_RBAC': True,
    'ENABLE_EXPLORE_JSON_CSRF_PROTECTION': False,
    'ENABLE_ROW_LEVEL_SECURITY': True,
    'ENABLE_TAGGING_SYSTEM': True,
    'GLOBAL_ASYNC_QUERIES': True,
    'VERSIONED_EXPORT': True,
}

# Настройки базы данных
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

# Настройки аутентификации
AUTH_TYPE = 'AUTH_DB'
AUTH_USER_REGISTRATION = False
AUTH_USER_REGISTRATION_ROLE = "Public"

# Настройки безопасности
ENABLE_ROW_LEVEL_SECURITY = True
ENABLE_TAGGING_SYSTEM = True

# Настройки производительности
SUPERSET_WEBSERVER_TIMEOUT = 60
SUPERSET_WEBSERVER_WORKERS = 4

# Настройки метрик
ENABLE_TELEMETRY = False

# Настройки экспорта
EXPORT_FORMATS = ['CSV', 'JSON', 'XLSX']
EXPORT_MAX_ROWS = 100000

# Настройки алертов
ALERT_REPORTS_NOTIFICATION_DRY_RUN = False
WEBDRIVER_BASEURL = "http://superset:8088/"
WEBDRIVER_BASEURL_USER_FRIENDLY = "http://localhost:8088/"
