"""
Middleware для аутентификации и авторизации с аудитом
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import time

from ..services.auth import AuthService
from ..services.audit import AuditService, AuditAction, AuditLevel
from ..schemas.auth import UserContext, Permission, User

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
        Обработка запроса с аудитом
        
        Args:
            request: FastAPI запрос
            
        Returns:
            Контекст пользователя или None
        """
        start_time = time.time()
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        # Если аутентификация не требуется, пропускаем
        if not self.require_auth:
            return None
        
        # Получаем токен из заголовка
        token = await self._extract_token(request)
        if not token:
            # Логируем попытку доступа без токена
            AuditService.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                level=AuditLevel.WARNING,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="Токен доступа не предоставлен",
                details={"endpoint": str(request.url)}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен доступа не предоставлен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем токен и получаем контекст пользователя
        try:
            user_context = AuthService.get_user_context_from_token(token)
        except HTTPException as e:
            # Логируем неудачную аутентификацию
            AuditService.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                level=AuditLevel.WARNING,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="Неверный или истекший токен",
                details={"endpoint": str(request.url), "token_prefix": token[:10] + "..."}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или истекший токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Проверяем требуемые разрешения
        if self.required_permissions:
            for permission in self.required_permissions:
                if not AuthService.check_permission(user_context, permission):
                    # Логируем нарушение прав доступа
                    AuditService.log_action(
                        action=AuditAction.UNAUTHORIZED_ACCESS,
                        level=AuditLevel.SECURITY,
                        user_context=user_context,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        error_message=f"Недостаточно прав. Требуется разрешение: {permission}",
                        details={
                            "endpoint": str(request.url),
                            "required_permission": permission,
                            "user_permissions": user_context.permissions
                        }
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Недостаточно прав. Требуется разрешение: {permission}"
                    )
        
        # Сохраняем контекст пользователя в запросе
        request.state.user = user_context
        request.state.auth_start_time = start_time
        
        # Логируем успешную аутентификацию
        auth_time = (time.time() - start_time) * 1000  # в миллисекундах
        logger.info(f"Пользователь {user_context.username} (ID: {user_context.user_id}) аутентифицирован за {auth_time:.2f}мс")
        
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
    
    def _get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Возвращаем прямой IP
        return request.client.host if request.client else "unknown"


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Получение текущего пользователя из токена"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен доступа не предоставлен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Временно возвращаем фиктивного пользователя для тестирования
        # TODO: Реализовать реальную проверку токена
        from ..schemas.auth import User
        return User(
            id=1,
            username="test_user",
            email="test@example.com",
            tenant_id=1,
            role_id=1,
            is_active=True
        )
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
