"""
Роутер для аутентификации и управления пользователями
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from typing import List, Optional
import logging

from ..schemas.auth import (
    User, UserCreate, UserUpdate, LoginRequest, TokenResponse, 
    RefreshTokenRequest, Role, Tenant, DocumentACL, DocumentACLCreate, UserContext
)
from ..services.auth import AuthService
from ..middleware.auth import get_current_user, require_permissions, require_tenant_access
from ..middleware.rate_limit import rate_limit
from ..schemas.common import PaginationParams, PaginatedResponse
from ..schemas.auth import Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Аутентификация"])

# Схема безопасности
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    Вход в систему
    
    Args:
        login_data: Данные для входа
        
    Returns:
        JWT токены доступа и обновления
    """
    try:
        # TODO: Реализовать проверку пользователя в базе данных
        # Пока используем заглушку для демонстрации
        
        # Проверяем учетные данные (в реальности - в базе данных)
        if login_data.username == "admin" and login_data.password == "admin123":
            user_data = {
                "user_id": 1,
                "username": "admin",
                "tenant_id": 1,
                "role_id": 1,
                "permissions": [Permission.ADMIN],
                "is_admin": True
            }
        elif login_data.username == "user" and login_data.password == "user123":
            user_data = {
                "user_id": 2,
                "username": "user",
                "tenant_id": 1,
                "role_id": 2,
                "permissions": [Permission.READ, Permission.WRITE],
                "is_admin": False
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные учетные данные"
            )
        
        # Создаем токены
        access_token = AuthService.create_access_token(user_data)
        refresh_token = AuthService.create_refresh_token(user_data)
        
        logger.info(f"Успешный вход пользователя {login_data.username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 минут
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка входа пользователя {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Обновление токена доступа
    
    Args:
        refresh_data: Данные для обновления токена
        
    Returns:
        Новый JWT токен доступа
    """
    try:
        # Проверяем refresh токен
        payload = AuthService.verify_token(refresh_data.refresh_token)
        
        # Проверяем тип токена
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный тип токена"
            )
        
        # Создаем новый access токен
        user_data = {
            "user_id": payload["user_id"],
            "username": payload["username"],
            "tenant_id": payload["tenant_id"],
            "role_id": payload["role_id"],
            "permissions": payload.get("permissions", []),
            "is_admin": payload.get("is_admin", False)
        }
        
        access_token = AuthService.create_access_token(user_data)
        
        logger.info(f"Токен обновлен для пользователя {user_data['username']}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=30 * 60  # 30 минут
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления токена: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: UserContext = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        Информация о пользователе
    """
    # TODO: Получить полную информацию о пользователе из базы данных
    return User(
        id=current_user.user_id,
        username=current_user.username,
        email="user@example.com",  # TODO: из базы данных
        tenant_id=current_user.tenant_id,
        role_id=current_user.role_id,
        is_active=True
        # created_at и last_login будут заполнены автоматически из default_factory
    )


@router.post("/users", response_model=User)
async def create_user(user_data: UserCreate, current_user: UserContext = Depends(get_current_user)):
    """
    Создание нового пользователя (только для администраторов)
    
    Args:
        user_data: Данные для создания пользователя
        current_user: Текущий пользователь
        
    Returns:
        Созданный пользователь
    """
    try:
        # TODO: Реализовать создание пользователя в базе данных
        
        # Проверяем, что пользователь создает пользователя в своем тенанте
        if current_user.tenant_id != user_data.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Можно создавать пользователей только в своем тенанте"
            )
        
        # Хешируем пароль
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        # TODO: Сохранить в базу данных
        
        logger.info(f"Пользователь {current_user.username} создал нового пользователя {user_data.username}")
        
        return User(
            id=999,  # TODO: ID из базы данных
            username=user_data.username,
            email=user_data.email,
            tenant_id=user_data.tenant_id,
            role_id=user_data.role_id,
            is_active=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка создания пользователя {user_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/users", response_model=PaginatedResponse[User])
async def get_users(
    pagination: PaginationParams = Depends(),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Получение списка пользователей (только для администраторов)
    
    Args:
        pagination: Параметры пагинации
        current_user: Текущий пользователь
        
    Returns:
        Список пользователей с пагинацией
    """
    try:
        # TODO: Реализовать получение пользователей из базы данных
        
        # Пока возвращаем заглушку
        users = [
            User(
                id=1,
                username="admin",
                email="admin@example.com",
                tenant_id=1,
                role_id=1,
                is_active=True
            ),
            User(
                id=2,
                username="user",
                email="user@example.com",
                tenant_id=1,
                role_id=2,
                is_active=True
            )
        ]
        
        # Применяем пагинацию
        start = (pagination.page - 1) * pagination.size
        end = start + pagination.size
        paginated_users = users[start:end]
        
        return PaginatedResponse(
            items=paginated_users,
            total=len(users),
            page=pagination.page,
            size=pagination.size,
            pages=(len(users) + pagination.size - 1) // pagination.size
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int, current_user: UserContext = Depends(get_current_user)):
    """
    Получение информации о пользователе по ID (только для администраторов)
    
    Args:
        user_id: ID пользователя
        current_user: Текущий пользователь
        
    Returns:
        Информация о пользователе
    """
    try:
        # TODO: Реализовать получение пользователя из базы данных
        
        # Проверяем, что пользователь запрашивает информацию о пользователе из своего тенанта
        # (в реальности - из базы данных)
        
        # Пока возвращаем заглушку
        if user_id == 1:
            return User(
                id=1,
                username="admin",
                email="admin@example.com",
                tenant_id=1,
                role_id=1,
                is_active=True
            )
        elif user_id == 2:
            return User(
                id=2,
                username="user",
                email="user@example.com",
                tenant_id=1,
                role_id=2,
                is_active=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Обновление пользователя (только для администраторов)
    
    Args:
        user_id: ID пользователя
        user_data: Данные для обновления
        current_user: Текущий пользователь
        
    Returns:
        Обновленный пользователь
    """
    try:
        # TODO: Реализовать обновление пользователя в базе данных
        
        # Проверяем, что пользователь обновляет пользователя из своего тенанта
        
        logger.info(f"Пользователь {current_user.username} обновил пользователя {user_id}")
        
        # Пока возвращаем заглушку
        return User(
            id=user_id,
            username=user_data.username or "user",
            email=user_data.email or "user@example.com",
            tenant_id=1,  # TODO: из базы данных
            role_id=user_data.role_id or 2,
            is_active=user_data.is_active if user_data.is_active is not None else True
        )
        
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/roles", response_model=List[Role])
async def get_roles():
    """
    Получение списка ролей
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        Список ролей
    """
    try:
        # TODO: Реализовать получение ролей из базы данных
        
        # Пока возвращаем заглушку
        roles = [
            Role(
                id=1,
                name="admin",
                tenant_id=1,
                permissions=[Permission.ADMIN]
            ),
            Role(
                id=2,
                name="user",
                tenant_id=1,
                permissions=[Permission.READ, Permission.WRITE]
            ),
            Role(
                id=3,
                name="readonly",
                tenant_id=1,
                permissions=[Permission.READ]
            )
        ]
        
        return roles
        
    except Exception as e:
        logger.error(f"Ошибка получения списка ролей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/tenants", response_model=List[Tenant])
async def get_tenants():
    """
    Получение списка тенантов
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        Список тенантов
    """
    try:
        # TODO: Реализовать получение тенантов из базы данных
        
        # Пока возвращаем заглушку
        tenants = [
            Tenant(
                id=1,
                name="Основная организация",
                domain="example.com"
            )
        ]
        
        return tenants
        
    except Exception as e:
        logger.error(f"Ошибка получения списка тенантов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )
