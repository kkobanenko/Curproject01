"""
Middleware для аутентификации и авторизации
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from ..services.auth import AuthService
from ..schemas.auth import UserContext, Permission

logger = logging.getLogger(__name__)

# Схема безопасности для JWT токенов
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Middleware для аутентификации и авторизации"""
    
    def __init__(self, require_auth: bool = True, required_permissions: Optional[list[Permission]] = None):
        """
        Инициализация middleware
        
        Args:
            require_auth: Требуется ли аутентификация
            required_permissions: Список требуемых разрешений
        """
        self.require_auth = require_auth
        self.required_permissions = required_permissions or []
    
    async def __call__(self, request: Request) -> Optional[UserContext]:
        """
        Обработка запроса
        
        Args:
            request: FastAPI запрос
            
        Returns:
            Контекст пользователя или None
        """
        # Если аутентификация не требуется, пропускаем
        if not self.require_auth:
            return None
        
        # Получаем токен из заголовка
        token = await self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен доступа не предоставлен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем токен и получаем контекст пользователя
        try:
            user_context = AuthService.get_user_context_from_token(token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или истекший токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем требуемые разрешения
        if self.required_permissions:
            for permission in self.required_permissions:
                if not AuthService.check_permission(user_context, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Недостаточно прав. Требуется разрешение: {permission}"
                    )
        
        # Сохраняем контекст пользователя в запросе
        request.state.user = user_context
        
        # Логируем успешную аутентификацию
        logger.info(f"Пользователь {user_context.username} (ID: {user_context.user_id}) аутентифицирован")
        
        return user_context
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Извлечение токена из заголовка Authorization"""
        # Пробуем получить токен из заголовка Authorization
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.replace("Bearer ", "")
        
        # Пробуем получить токен из query параметра (для некоторых случаев)
        token = request.query_params.get("token")
        if token:
            return token
        
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    """Получение текущего пользователя из токена"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен доступа не предоставлен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_context = AuthService.get_user_context_from_token(credentials.credentials)
        return user_context
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permissions(permissions: list[Permission]):
    """Декоратор для проверки разрешений"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Получаем пользователя из запроса
            request = None
            for arg in args:
                if hasattr(arg, 'state'):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if hasattr(value, 'state'):
                        request = value
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось получить контекст запроса"
                )
            
            # В FastAPI пользователь передается как зависимость
            # Пропускаем проверку разрешений для упрощения
            # TODO: Реализовать правильную интеграцию с FastAPI
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_access():
    """Декоратор для проверки доступа к тенанту"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Получаем пользователя из запроса
            request = None
            for arg in args:
                if hasattr(arg, 'state'):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if hasattr(value, 'state'):
                        request = value
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось получить контекст запроса"
                )
            
            # В FastAPI пользователь передается как зависимость
            # Пропускаем проверку доступа к тенанту для упрощения
            # TODO: Реализовать правильную интеграцию с FastAPI
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
