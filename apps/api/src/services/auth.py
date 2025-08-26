"""
Сервис аутентификации и авторизации
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status
import logging

from ..schemas.auth import UserContext, Permission, UserRole
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Секретный ключ для JWT (в продакшене должен быть в переменных окружения)
SECRET_KEY = settings.secret_key or "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Сервис для работы с аутентификацией и авторизацией"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Хеширование пароля"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Создание JWT токена доступа"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Создание JWT токена обновления"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Проверка JWT токена"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен истек"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен"
            )
    
    @staticmethod
    def get_user_context_from_token(token: str) -> UserContext:
        """Получение контекста пользователя из токена"""
        payload = AuthService.verify_token(token)
        
        # Проверяем тип токена
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена"
            )
        
        # Создаем контекст пользователя
        user_context = UserContext(
            user_id=payload["user_id"],
            username=payload["username"],
            tenant_id=payload["tenant_id"],
            role_id=payload["role_id"],
            permissions=payload.get("permissions", []),
            is_admin=payload.get("is_admin", False)
        )
        
        return user_context
    
    @staticmethod
    def check_permission(user_context: UserContext, required_permission: Permission) -> bool:
        """Проверка наличия разрешения у пользователя"""
        # Администраторы имеют все разрешения
        if user_context.is_admin:
            return True
        
        # Проверяем конкретное разрешение
        return required_permission in user_context.permissions
    
    @staticmethod
    def check_document_access(user_context: UserContext, document_tenant_id: int, 
                            document_permissions: list[Permission]) -> bool:
        """Проверка доступа к документу"""
        # Администраторы имеют доступ ко всем документам
        if user_context.is_admin:
            return True
        
        # Проверяем принадлежность к тому же тенанту
        if user_context.tenant_id != document_tenant_id:
            return False
        
        # Проверяем наличие хотя бы одного разрешения
        user_permissions = set(user_context.permissions)
        doc_permissions = set(document_permissions)
        
        return bool(user_permissions.intersection(doc_permissions))
    
    @staticmethod
    def get_token_expiration_info(token: str) -> Dict[str, Any]:
        """Получение информации об истечении токена"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            exp_timestamp = payload.get("exp")
            
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                now = datetime.utcnow()
                time_until_expiry = exp_datetime - now
                
                return {
                    "expires_at": exp_datetime.isoformat(),
                    "seconds_until_expiry": max(0, int(time_until_expiry.total_seconds())),
                    "is_expired": now > exp_datetime
                }
            else:
                return {"error": "Токен не содержит информации об истечении"}
                
        except jwt.JWTError:
            return {"error": "Неверный токен"}
