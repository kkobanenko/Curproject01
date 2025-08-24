"""
Конфигурация Superset для RAG-платформы
"""
import os

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
PERMANENT_SESSION_LIFETIME = 1800
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # В продакшене True

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
TIME_ROTATE_LOG_LEVEL = 'DEBUG'

# Настройки функций
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_RBAC': True,
    'ENABLE_EXPLORE_JSON_CSRF_PROTECTION': False,
}

# Настройки базы данных
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
