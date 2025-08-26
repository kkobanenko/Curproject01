"""
Схемы для аутентификации, ролей и ACL
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Роли пользователей"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    GUEST = "guest"


class Permission(str, Enum):
    """Разрешения для документов"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"


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
