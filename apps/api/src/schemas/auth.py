"""
Схемы для аутентификации, ролей и ACL
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Роли пользователей"""
    SUPER_ADMIN = "super_admin"      # Полный доступ ко всем тенантам
    ADMIN = "admin"                  # Полный доступ в рамках тенанта
    USER = "user"                    # Стандартный пользователь
    VIEWER = "viewer"                # Только просмотр документов
    READONLY = "readonly"            # Только чтение без изменений
    GUEST = "guest"                  # Минимальные права доступа


class Permission(str, Enum):
    """Разрешения для документов"""
    # Базовые разрешения
    READ = "read"                    # Чтение документов
    WRITE = "write"                  # Создание/изменение документов
    DELETE = "delete"                # Удаление документов
    SHARE = "share"                  # Предоставление доступа
    
    # Административные разрешения
    ADMIN = "admin"                  # Полные права в тенанте
    USER_MANAGEMENT = "user_mgmt"    # Управление пользователями
    ROLE_MANAGEMENT = "role_mgmt"    # Управление ролями
    TENANT_SETTINGS = "tenant_settings"  # Настройки тенанта
    
    # Системные разрешения
    AUDIT_VIEW = "audit_view"        # Просмотр логов аудита
    METRICS_VIEW = "metrics_view"    # Просмотр метрик
    SYSTEM_CONFIG = "system_config"  # Системные настройки
    
    # API разрешения
    API_ACCESS = "api_access"        # Доступ к API
    BULK_OPERATIONS = "bulk_ops"     # Массовые операции
    EXPORT_DATA = "export_data"      # Экспорт данных


class Tenant(BaseModel):
    """Модель тенанта (организации)"""
    id: int = Field(..., description="ID тенанта")
    name: str = Field(..., description="Название организации")
    domain: Optional[str] = Field(None, description="Домен организации")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Активен ли тенант")


class Role(BaseModel):
    """Модель роли"""
    id: int = Field(..., description="ID роли")
    name: str = Field(..., description="Название роли")
    tenant_id: int = Field(..., description="ID тенанта")
    permissions: List[Permission] = Field(default=[Permission.READ], description="Разрешения роли")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Активна ли роль")


class User(BaseModel):
    """Модель пользователя"""
    id: int = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    tenant_id: int = Field(..., description="ID тенанта")
    role_id: int = Field(..., description="ID роли")
    is_active: bool = Field(default=True, description="Активен ли пользователь")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None, description="Последний вход")


class UserCreate(BaseModel):
    """Схема создания пользователя"""
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=8, description="Пароль")
    tenant_id: int = Field(..., description="ID тенанта")
    role_id: int = Field(..., description="ID роли")


class UserUpdate(BaseModel):
    """Схема обновления пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    """Схема входа в систему"""
    username: str = Field(..., description="Имя пользователя или email")
    password: str = Field(..., description="Пароль")


class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    access_token: str = Field(..., description="JWT токен доступа")
    token_type: str = Field(default="bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни токена в секундах")
    refresh_token: Optional[str] = Field(None, description="Токен обновления")


class RefreshTokenRequest(BaseModel):
    """Схема обновления токена"""
    refresh_token: str = Field(..., description="Токен обновления")


class DocumentACL(BaseModel):
    """Модель ACL для документа"""
    id: int = Field(..., description="ID записи ACL")
    document_id: int = Field(..., description="ID документа")
    tenant_id: int = Field(..., description="ID тенанта")
    role_id: Optional[int] = Field(None, description="ID роли (None для всех ролей)")
    user_id: Optional[int] = Field(None, description="ID пользователя (None для всех пользователей)")
    permissions: List[Permission] = Field(..., description="Разрешения")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(..., description="ID пользователя, создавшего ACL")


class DocumentACLCreate(BaseModel):
    """Схема создания ACL для документа"""
    document_id: int = Field(..., description="ID документа")
    tenant_id: int = Field(..., description="ID тенанта")
    role_id: Optional[int] = Field(None, description="ID роли")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    permissions: List[Permission] = Field(..., description="Разрешения")


class UserContext(BaseModel):
    """Контекст пользователя для middleware"""
    user_id: int = Field(..., description="ID пользователя")
    username: str = Field(..., description="Имя пользователя")
    tenant_id: int = Field(..., description="ID тенанта")
    role_id: int = Field(..., description="ID роли")
    permissions: List[Permission] = Field(..., description="Разрешения пользователя")
    is_admin: bool = Field(..., description="Является ли администратором")


class RateLimitInfo(BaseModel):
    """Информация о rate limiting"""
    remaining: int = Field(..., description="Оставшиеся запросы")
    reset_time: datetime = Field(..., description="Время сброса лимита")
    limit: int = Field(..., description="Общий лимит запросов")


class SessionInfo(BaseModel):
    """Информация о сессии пользователя"""
    session_id: str = Field(..., description="ID сессии")
    user_id: int = Field(..., description="ID пользователя")
    ip_address: str = Field(..., description="IP адрес")
    user_agent: str = Field(..., description="User-Agent")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Время истечения сессии")
    is_active: bool = Field(default=True, description="Активна ли сессия")


class SecuritySettings(BaseModel):
    """Настройки безопасности для тенанта"""
    tenant_id: int = Field(..., description="ID тенанта")
    password_min_length: int = Field(default=8, description="Минимальная длина пароля")
    password_require_uppercase: bool = Field(default=True, description="Требовать заглавные буквы")
    password_require_lowercase: bool = Field(default=True, description="Требовать строчные буквы")
    password_require_numbers: bool = Field(default=True, description="Требовать цифры")
    password_require_symbols: bool = Field(default=False, description="Требовать спецсимволы")
    password_expiry_days: Optional[int] = Field(None, description="Срок действия пароля в днях")
    
    max_login_attempts: int = Field(default=5, description="Максимум попыток входа")
    account_lockout_duration: int = Field(default=300, description="Блокировка аккаунта в секундах")
    
    session_timeout_minutes: int = Field(default=480, description="Таймаут сессии в минутах")
    max_concurrent_sessions: int = Field(default=3, description="Максимум одновременных сессий")
    
    require_2fa: bool = Field(default=False, description="Требовать двухфакторную аутентификацию")
    allowed_ip_ranges: Optional[List[str]] = Field(None, description="Разрешенные IP диапазоны")
    
    data_encryption_enabled: bool = Field(default=True, description="Включено ли шифрование данных")
    audit_logging_enabled: bool = Field(default=True, description="Включено ли логирование аудита")


class PermissionSet(BaseModel):
    """Набор разрешений для роли"""
    role_name: str = Field(..., description="Название роли")
    permissions: List[Permission] = Field(..., description="Список разрешений")
    description: Optional[str] = Field(None, description="Описание набора разрешений")


class SecurityAlert(BaseModel):
    """Уведомление о событии безопасности"""
    id: Optional[int] = None
    tenant_id: int = Field(..., description="ID тенанта")
    alert_type: str = Field(..., description="Тип уведомления")
    severity: str = Field(..., description="Критичность: low, medium, high, critical")
    title: str = Field(..., description="Заголовок уведомления")
    message: str = Field(..., description="Сообщение")
    details: Dict[str, Any] = Field(default={}, description="Дополнительные детали")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = Field(default=False, description="Решено ли уведомление")
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None


class AuditLogEntry(BaseModel):
    """Запись в логе аудита"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[int] = Field(None, description="ID пользователя")
    username: Optional[str] = Field(None, description="Имя пользователя")
    tenant_id: Optional[int] = Field(None, description="ID тенанта")
    action: str = Field(..., description="Выполненное действие")
    resource_type: Optional[str] = Field(None, description="Тип ресурса")
    resource_id: Optional[str] = Field(None, description="ID ресурса")
    ip_address: Optional[str] = Field(None, description="IP адрес")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    success: bool = Field(default=True, description="Успешность операции")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    details: Dict[str, Any] = Field(default={}, description="Дополнительные детали")


class TwoFactorAuth(BaseModel):
    """Настройки двухфакторной аутентификации"""
    user_id: int = Field(..., description="ID пользователя")
    is_enabled: bool = Field(default=False, description="Включена ли 2FA")
    method: Optional[str] = Field(None, description="Метод 2FA: totp, sms, email")
    secret_key: Optional[str] = Field(None, description="Секретный ключ для TOTP")
    backup_codes: Optional[List[str]] = Field(None, description="Резервные коды")
    phone_number: Optional[str] = Field(None, description="Номер телефона для SMS")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


class TokenBlacklist(BaseModel):
    """Черный список токенов"""
    token_jti: str = Field(..., description="JWT ID токена")
    user_id: int = Field(..., description="ID пользователя")
    expires_at: datetime = Field(..., description="Время истечения токена")
    reason: str = Field(..., description="Причина добавления в черный список")
    created_at: datetime = Field(default_factory=datetime.utcnow)
