"""
Сервис шифрования данных в покое
"""
import os
import base64
import hashlib
from typing import Optional, Dict, Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
import json

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EncryptionService:
    """Сервис для шифрования данных в покое"""
    
    def __init__(self):
        """Инициализация сервиса шифрования"""
        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Получение ключа шифрования"""
        # В продакшене ключ должен храниться в безопасном месте (HSM, Key Vault)
        secret_key = settings.secret_key or "default-secret-key-change-in-production"
        
        # Генерируем ключ из секрета с помощью PBKDF2
        salt = b"rag-platform-salt"  # В продакшене используйте случайную соль
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key
    
    def encrypt_text(self, text: str) -> str:
        """
        Шифрование текста
        
        Args:
            text: Исходный текст
            
        Returns:
            Зашифрованный текст в base64
        """
        if not text:
            return text
        
        try:
            encrypted_data = self.fernet.encrypt(text.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('ascii')
        except Exception as e:
            logger.error(f"Ошибка шифрования текста: {e}")
            raise
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Расшифровка текста
        
        Args:
            encrypted_text: Зашифрованный текст в base64
            
        Returns:
            Расшифрованный текст
        """
        if not encrypted_text:
            return encrypted_text
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode('ascii'))
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка расшифровки текста: {e}")
            raise
    
    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """
        Шифрование JSON данных
        
        Args:
            data: Данные для шифрования
            
        Returns:
            Зашифрованные данные в base64
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return self.encrypt_text(json_str)
        except Exception as e:
            logger.error(f"Ошибка шифрования JSON: {e}")
            raise
    
    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Расшифровка JSON данных
        
        Args:
            encrypted_data: Зашифрованные данные
            
        Returns:
            Расшифрованные данные
        """
        try:
            json_str = self.decrypt_text(encrypted_data)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Ошибка расшифровки JSON: {e}")
            raise
    
    def encrypt_file_content(self, content: bytes) -> bytes:
        """
        Шифрование содержимого файла
        
        Args:
            content: Содержимое файла
            
        Returns:
            Зашифрованное содержимое
        """
        try:
            return self.fernet.encrypt(content)
        except Exception as e:
            logger.error(f"Ошибка шифрования файла: {e}")
            raise
    
    def decrypt_file_content(self, encrypted_content: bytes) -> bytes:
        """
        Расшифровка содержимого файла
        
        Args:
            encrypted_content: Зашифрованное содержимое
            
        Returns:
            Расшифрованное содержимое
        """
        try:
            return self.fernet.decrypt(encrypted_content)
        except Exception as e:
            logger.error(f"Ошибка расшифровки файла: {e}")
            raise
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """
        Хеширование пароля с солью
        
        Args:
            password: Пароль для хеширования
            salt: Соль (если не указана, генерируется новая)
            
        Returns:
            Словарь с хешем и солью
        """
        if salt is None:
            salt = base64.urlsafe_b64encode(os.urandom(32)).decode('ascii')
        
        # Используем PBKDF2 для хеширования пароля
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode('ascii'),
            iterations=100000,
            backend=default_backend()
        )
        
        password_hash = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8'))).decode('ascii')
        
        return {
            "hash": password_hash,
            "salt": salt
        }
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        Проверка пароля
        
        Args:
            password: Проверяемый пароль
            password_hash: Сохраненный хеш
            salt: Соль
            
        Returns:
            True если пароль верный
        """
        try:
            computed_hash = self.hash_password(password, salt)["hash"]
            return computed_hash == password_hash
        except Exception as e:
            logger.error(f"Ошибка проверки пароля: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Генерация безопасного токена
        
        Args:
            length: Длина токена в байтах
            
        Returns:
            Токен в base64
        """
        return base64.urlsafe_b64encode(os.urandom(length)).decode('ascii')
    
    def hash_data(self, data: Union[str, bytes]) -> str:
        """
        Хеширование данных с помощью SHA-256
        
        Args:
            data: Данные для хеширования
            
        Returns:
            Хеш в hex формате
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()


class DocumentEncryption:
    """Специализированное шифрование для документов"""
    
    def __init__(self):
        self.encryption_service = EncryptionService()
    
    def encrypt_document_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Шифрование метаданных документа
        
        Args:
            metadata: Метаданные документа
            
        Returns:
            Зашифрованные метаданные
        """
        # Исключаем из шифрования поля, которые нужны для поиска
        searchable_fields = ["title", "filename", "document_type", "tenant_id"]
        
        encrypted_metadata = {}
        plain_metadata = {}
        
        for key, value in metadata.items():
            if key in searchable_fields:
                plain_metadata[key] = value
            else:
                encrypted_metadata[key] = value
        
        # Шифруем чувствительные метаданные
        if encrypted_metadata:
            plain_metadata["encrypted_fields"] = self.encryption_service.encrypt_json(encrypted_metadata)
        
        return json.dumps(plain_metadata, ensure_ascii=False)
    
    def decrypt_document_metadata(self, encrypted_metadata: str) -> Dict[str, Any]:
        """
        Расшифровка метаданных документа
        
        Args:
            encrypted_metadata: Зашифрованные метаданные
            
        Returns:
            Расшифрованные метаданные
        """
        metadata = json.loads(encrypted_metadata)
        
        # Расшифровываем зашифрованные поля
        if "encrypted_fields" in metadata:
            encrypted_fields = self.encryption_service.decrypt_json(metadata["encrypted_fields"])
            del metadata["encrypted_fields"]
            metadata.update(encrypted_fields)
        
        return metadata
    
    def encrypt_document_content(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        """
        Шифрование содержимого документа
        
        Args:
            content: Содержимое документа
            content_type: Тип содержимого
            
        Returns:
            Информация о зашифрованном содержимом
        """
        content_bytes = content.encode('utf-8') if isinstance(content, str) else content
        
        # Генерируем уникальный ключ для документа
        document_key = self.encryption_service.generate_secure_token()
        
        # Шифруем содержимое
        encrypted_content = self.encryption_service.encrypt_file_content(content_bytes)
        
        # Создаем хеш для проверки целостности
        content_hash = self.encryption_service.hash_data(content_bytes)
        
        return {
            "encrypted_content": base64.urlsafe_b64encode(encrypted_content).decode('ascii'),
            "content_hash": content_hash,
            "content_type": content_type,
            "encryption_version": "1.0"
        }
    
    def decrypt_document_content(self, encrypted_info: Dict[str, Any]) -> str:
        """
        Расшифровка содержимого документа
        
        Args:
            encrypted_info: Информация о зашифрованном содержимом
            
        Returns:
            Расшифрованное содержимое
        """
        encrypted_content = base64.urlsafe_b64decode(encrypted_info["encrypted_content"].encode('ascii'))
        
        # Расшифровываем содержимое
        decrypted_content = self.encryption_service.decrypt_file_content(encrypted_content)
        
        # Проверяем целостность
        computed_hash = self.encryption_service.hash_data(decrypted_content)
        if computed_hash != encrypted_info["content_hash"]:
            raise ValueError("Нарушена целостность документа")
        
        return decrypted_content.decode('utf-8')


class PII_Encryption:
    """Шифрование персональных данных (PII)"""
    
    def __init__(self):
        self.encryption_service = EncryptionService()
    
    def encrypt_pii_field(self, value: str, field_type: str) -> Dict[str, str]:
        """
        Шифрование поля с персональными данными
        
        Args:
            value: Значение для шифрования
            field_type: Тип поля (email, phone, ssn, etc.)
            
        Returns:
            Зашифрованное значение с метаданными
        """
        encrypted_value = self.encryption_service.encrypt_text(value)
        
        # Создаем частичный хеш для поиска (первые 4 символа)
        if field_type == "email":
            search_hint = value.split("@")[0][:3] + "***@" + value.split("@")[1] if "@" in value else "***"
        elif field_type == "phone":
            search_hint = value[:3] + "*" * (len(value) - 3) if len(value) > 3 else "***"
        else:
            search_hint = value[:2] + "*" * (len(value) - 2) if len(value) > 2 else "***"
        
        return {
            "encrypted_value": encrypted_value,
            "field_type": field_type,
            "search_hint": search_hint,
            "value_hash": self.encryption_service.hash_data(value.lower())[:8]  # Первые 8 символов хеша
        }
    
    def decrypt_pii_field(self, encrypted_field: Dict[str, str]) -> str:
        """
        Расшифровка поля с персональными данными
        
        Args:
            encrypted_field: Зашифрованное поле
            
        Returns:
            Расшифрованное значение
        """
        return self.encryption_service.decrypt_text(encrypted_field["encrypted_value"])


# Глобальные экземпляры сервисов
encryption_service = EncryptionService()
document_encryption = DocumentEncryption()
pii_encryption = PII_Encryption()


def encrypt_sensitive_data(data: Any, field_name: str) -> Any:
    """
    Вспомогательная функция для шифрования чувствительных данных
    
    Args:
        data: Данные для шифрования
        field_name: Имя поля
        
    Returns:
        Зашифрованные данные
    """
    if data is None:
        return None
    
    # Определяем тип поля для правильного шифрования
    pii_fields = ["email", "phone", "passport", "social_security", "credit_card"]
    
    if field_name.lower() in pii_fields:
        return pii_encryption.encrypt_pii_field(str(data), field_name.lower())
    else:
        return encryption_service.encrypt_text(str(data))


def decrypt_sensitive_data(encrypted_data: Any, field_name: str) -> Any:
    """
    Вспомогательная функция для расшифровки чувствительных данных
    
    Args:
        encrypted_data: Зашифрованные данные
        field_name: Имя поля
        
    Returns:
        Расшифрованные данные
    """
    if encrypted_data is None:
        return None
    
    if isinstance(encrypted_data, dict) and "encrypted_value" in encrypted_data:
        # PII поле
        return pii_encryption.decrypt_pii_field(encrypted_data)
    else:
        # Обычное зашифрованное поле
        return encryption_service.decrypt_text(str(encrypted_data))
