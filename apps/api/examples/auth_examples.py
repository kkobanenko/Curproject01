"""
Примеры использования API аутентификации
"""
import requests
import json
from typing import Dict, Any

# Базовый URL API
BASE_URL = "http://localhost:8080/api/v1"


class RAGAuthClient:
    """Клиент для работы с API аутентификации RAG Platform"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.session = requests.Session()
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Вход в систему
        
        Args:
            username: Имя пользователя
            password: Пароль
            
        Returns:
            Ответ с токенами
        """
        url = f"{self.base_url}/auth/login"
        data = {
            "username": username,
            "password": password
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        self.access_token = result["access_token"]
        self.refresh_token = result["refresh_token"]
        
        # Устанавливаем заголовок авторизации для всех последующих запросов
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
        
        return result
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Обновление токена доступа
        
        Returns:
            Новый токен доступа
        """
        if not self.refresh_token:
            raise ValueError("Refresh token не найден. Сначала выполните вход.")
        
        url = f"{self.base_url}/auth/refresh"
        data = {
            "refresh_token": self.refresh_token
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        self.access_token = result["access_token"]
        
        # Обновляем заголовок авторизации
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
        
        return result
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        Получение информации о текущем пользователе
        
        Returns:
            Информация о пользователе
        """
        url = f"{self.base_url}/auth/me"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def get_users(self, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """
        Получение списка пользователей (только для администраторов)
        
        Args:
            page: Номер страницы
            size: Размер страницы
            
        Returns:
            Список пользователей с пагинацией
        """
        url = f"{self.base_url}/auth/users"
        params = {
            "page": page,
            "size": size
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Получение информации о пользователе по ID (только для администраторов)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Информация о пользователе
        """
        url = f"{self.base_url}/auth/users/{user_id}"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание нового пользователя (только для администраторов)
        
        Args:
            user_data: Данные пользователя
            
        Returns:
            Созданный пользователь
        """
        url = f"{self.base_url}/auth/users"
        response = self.session.post(url, json=user_data)
        response.raise_for_status()
        
        return response.json()
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление пользователя (только для администраторов)
        
        Args:
            user_id: ID пользователя
            user_data: Данные для обновления
            
        Returns:
            Обновленный пользователь
        """
        url = f"{self.base_url}/auth/users/{user_id}"
        response = self.session.put(url, json=user_data)
        response.raise_for_status()
        
        return response.json()
    
    def get_roles(self) -> Dict[str, Any]:
        """
        Получение списка ролей
        
        Returns:
            Список ролей
        """
        url = f"{self.base_url}/auth/roles"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def get_tenants(self) -> Dict[str, Any]:
        """
        Получение списка тенантов
        
        Returns:
            Список тенантов
        """
        url = f"{self.base_url}/auth/tenants"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def logout(self):
        """Выход из системы (очистка токенов)"""
        self.access_token = None
        self.refresh_token = None
        self.session.headers.pop("Authorization", None)


def example_usage():
    """Пример использования клиента аутентификации"""
    
    print("🔐 Пример использования API аутентификации RAG Platform\n")
    
    # Создаем клиент
    client = RAGAuthClient()
    
    try:
        # 1. Вход в систему как администратор
        print("1️⃣ Вход в систему как администратор...")
        login_result = client.login("admin", "admin123")
        print(f"✅ Успешный вход: {login_result['token_type']} токен получен")
        print(f"⏰ Токен действителен: {login_result['expires_in']} секунд\n")
        
        # 2. Получение информации о текущем пользователе
        print("2️⃣ Получение информации о текущем пользователе...")
        user_info = client.get_current_user()
        print(f"👤 Пользователь: {user_info['username']}")
        print(f"🏢 Тенант: {user_info['tenant_id']}")
        print(f"🔑 Роль: {user_info['role_id']}\n")
        
        # 3. Получение списка пользователей
        print("3️⃣ Получение списка пользователей...")
        users = client.get_users(page=1, size=10)
        print(f"📋 Всего пользователей: {users['total']}")
        print(f"📄 Страница: {users['page']} из {users['pages']}")
        for user in users['items']:
            print(f"   - {user['username']} ({user['email']})")
        print()
        
        # 4. Получение ролей
        print("4️⃣ Получение списка ролей...")
        roles = client.get_roles()
        for role in roles:
            print(f"   - {role['name']}: {', '.join(role['permissions'])}")
        print()
        
        # 5. Получение тенантов
        print("5️⃣ Получение списка тенантов...")
        tenants = client.get_tenants()
        for tenant in tenants:
            print(f"   - {tenant['name']} ({tenant['domain']})")
        print()
        
        # 6. Выход из системы
        print("6️⃣ Выход из системы...")
        client.logout()
        print("✅ Выход выполнен успешно")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка HTTP запроса: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def example_user_management():
    """Пример управления пользователями"""
    
    print("👥 Пример управления пользователями\n")
    
    client = RAGAuthClient()
    
    try:
        # Вход как администратор
        client.login("admin", "admin123")
        
        # Создание нового пользователя
        print("1️⃣ Создание нового пользователя...")
        new_user = client.create_user({
            "username": "test_user",
            "email": "test@example.com",
            "password": "secure_password_123",
            "tenant_id": 1,
            "role_id": 2
        })
        print(f"✅ Пользователь создан: {new_user['username']} (ID: {new_user['id']})")
        
        # Получение информации о пользователе
        print("\n2️⃣ Получение информации о пользователе...")
        user_info = client.get_user(new_user['id'])
        print(f"👤 {user_info['username']} - {user_info['email']}")
        
        # Обновление пользователя
        print("\n3️⃣ Обновление пользователя...")
        updated_user = client.update_user(new_user['id'], {
            "email": "updated@example.com"
        })
        print(f"✅ Email обновлен: {updated_user['email']}")
        
        # Выход
        client.logout()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def example_rate_limiting():
    """Пример работы с rate limiting"""
    
    print("⏱️ Пример работы с rate limiting\n")
    
    client = RAGAuthClient()
    
    try:
        # Попытка множественных запросов для демонстрации rate limiting
        print("Попытка множественных запросов для демонстрации rate limiting...")
        
        for i in range(15):
            try:
                response = client.session.post(f"{BASE_URL}/auth/login", json={
                    "username": "admin",
                    "password": "admin123"
                })
                
                if response.status_code == 429:
                    print(f"🚫 Rate limit достигнут на запросе {i+1}")
                    print(f"   Заголовки: {dict(response.headers)}")
                    break
                else:
                    print(f"✅ Запрос {i+1} выполнен успешно")
                    
            except Exception as e:
                print(f"❌ Ошибка на запросе {i+1}: {e}")
                break
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    print("🚀 Запуск примеров API аутентификации\n")
    
    # Основной пример
    example_usage()
    
    print("\n" + "="*50 + "\n")
    
    # Управление пользователями
    example_user_management()
    
    print("\n" + "="*50 + "\n")
    
    # Rate limiting
    example_rate_limiting()
    
    print("\n✨ Примеры завершены!")
