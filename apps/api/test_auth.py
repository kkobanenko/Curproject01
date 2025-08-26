"""
Тест аутентификации и авторизации
"""
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.main import app
from src.services.auth import AuthService
from src.schemas.auth import Permission

client = TestClient(app)


def test_login_success():
    """Тест успешного входа"""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800  # 30 минут


def test_login_invalid_credentials():
    """Тест входа с неверными учетными данными"""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    
    assert response.status_code == 401
    assert "Неверные учетные данные" in response.json()["detail"]


def test_refresh_token():
    """Тест обновления токена"""
    # Сначала получаем токены
    login_response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    refresh_token = login_response.json()["refresh_token"]
    
    # Обновляем токен
    response = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_protected_endpoint_without_token():
    """Тест доступа к защищенному эндпоинту без токена"""
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 401
    assert "Токен доступа не предоставлен" in response.json()["detail"]


def test_protected_endpoint_with_token():
    """Тест доступа к защищенному эндпоинту с токеном"""
    # Получаем токен
    login_response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    access_token = login_response.json()["access_token"]
    
    # Используем токен для доступа к защищенному эндпоинту
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["tenant_id"] == 1


def test_admin_only_endpoint():
    """Тест доступа к эндпоинту только для администраторов"""
    # Получаем токен обычного пользователя
    login_response = client.post("/api/v1/auth/login", json={
        "username": "user",
        "password": "user123"
    })
    
    access_token = login_response.json()["access_token"]
    
    # Пытаемся получить список пользователей (только для админов)
    response = client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 403
    assert "Недостаточно прав" in response.json()["detail"]


def test_admin_endpoint_access():
    """Тест доступа администратора к защищенным эндпоинтам"""
    # Получаем токен администратора
    login_response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    access_token = login_response.json()["access_token"]
    
    # Получаем список пользователей
    response = client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0


def test_rate_limiting():
    """Тест rate limiting"""
    # Пытаемся войти много раз подряд
    for i in range(15):  # Больше лимита в 10 запросов в минуту
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 429:  # Too Many Requests
            break
    else:
        # Если не получили 429, проверяем заголовки rate limiting
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


def test_jwt_token_creation():
    """Тест создания JWT токенов"""
    user_data = {
        "user_id": 1,
        "username": "test_user",
        "tenant_id": 1,
        "role_id": 1,
        "permissions": [Permission.READ],
        "is_admin": False
    }
    
    # Создаем токен
    access_token = AuthService.create_access_token(user_data)
    refresh_token = AuthService.create_refresh_token(user_data)
    
    # Проверяем, что токены созданы
    assert access_token is not None
    assert refresh_token is not None
    
    # Проверяем содержимое токена
    payload = AuthService.verify_token(access_token)
    assert payload["user_id"] == 1
    assert payload["username"] == "test_user"
    assert payload["type"] == "access"


def test_password_hashing():
    """Тест хеширования паролей"""
    password = "test_password_123"
    
    # Хешируем пароль
    hashed = AuthService.get_password_hash(password)
    
    # Проверяем, что хеш отличается от оригинального пароля
    assert hashed != password
    
    # Проверяем пароль
    assert AuthService.verify_password(password, hashed) is True
    
    # Проверяем неверный пароль
    assert AuthService.verify_password("wrong_password", hashed) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
