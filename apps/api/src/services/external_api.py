"""
Сервис для интеграции с внешними API (CRM, ERP, и др.)
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
import httpx
from abc import ABC, abstractmethod

from ..schemas.webhooks import ExternalAPIConfig, IntegrationEvent
from ..schemas.auth import UserContext
from ..services.audit import AuditService, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class BaseAPIConnector(ABC):
    """Базовый класс для подключения к внешним API"""
    
    def __init__(self, config: ExternalAPIConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=str(config.base_url),
            timeout=config.timeout_seconds
        )
        self.auth_headers = {}
        self.rate_limiter = RateLimiter(config.rate_limit_requests)
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Аутентификация в внешнем API"""
        pass
    
    @abstractmethod
    async def sync_data(self, data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Синхронизация данных"""
        pass
    
    async def test_connection(self) -> bool:
        """Тестирование подключения"""
        try:
            response = await self.client.get("/health", headers=self.auth_headers)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения к {self.config.name}: {e}")
            return False
    
    async def close(self):
        """Закрытие подключения"""
        await self.client.aclose()


class CRMConnector(BaseAPIConnector):
    """Коннектор для CRM систем"""
    
    async def authenticate(self) -> bool:
        """Аутентификация в CRM"""
        auth_config = self.config.auth_config
        
        if self.config.auth_type == "api_key":
            self.auth_headers["Authorization"] = f"Bearer {auth_config['api_key']}"
            return True
            
        elif self.config.auth_type == "oauth2":
            # OAuth2 аутентификация
            token_url = auth_config.get("token_url")
            client_id = auth_config.get("client_id")
            client_secret = auth_config.get("client_secret")
            
            response = await self.client.post(token_url, data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            })
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_headers["Authorization"] = f"Bearer {token_data['access_token']}"
                return True
                
        elif self.config.auth_type == "basic":
            username = auth_config.get("username")
            password = auth_config.get("password")
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.auth_headers["Authorization"] = f"Basic {credentials}"
            return True
        
        return False
    
    async def sync_data(self, data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Синхронизация данных с CRM"""
        await self.rate_limiter.acquire()
        
        try:
            # Маппинг полей
            mapped_data = self._map_fields(data, self.config.field_mapping)
            
            if operation == "create":
                response = await self.client.post(
                    "/contacts",
                    json=mapped_data,
                    headers=self.auth_headers
                )
            elif operation == "update":
                contact_id = mapped_data.get("id")
                response = await self.client.put(
                    f"/contacts/{contact_id}",
                    json=mapped_data,
                    headers=self.auth_headers
                )
            elif operation == "get":
                contact_id = data.get("id")
                response = await self.client.get(
                    f"/contacts/{contact_id}",
                    headers=self.auth_headers
                )
            else:
                raise ValueError(f"Неподдерживаемая операция: {operation}")
            
            if response.status_code < 300:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            logger.error(f"Ошибка синхронизации с CRM: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _map_fields(self, data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Маппинг полей согласно конфигурации"""
        mapped = {}
        
        for source_field, target_field in mapping.items():
            if source_field in data:
                mapped[target_field] = data[source_field]
        
        # Добавляем немаппленные поля как есть
        for key, value in data.items():
            if key not in mapping and key not in mapped:
                mapped[key] = value
        
        return mapped


class ERPConnector(BaseAPIConnector):
    """Коннектор для ERP систем"""
    
    async def authenticate(self) -> bool:
        """Аутентификация в ERP"""
        # Аналогично CRM, но может иметь специфику ERP
        return await super().authenticate()
    
    async def sync_data(self, data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Синхронизация данных с ERP"""
        await self.rate_limiter.acquire()
        
        try:
            # ERP специфическая логика
            if operation == "create_invoice":
                return await self._create_invoice(data)
            elif operation == "update_inventory":
                return await self._update_inventory(data)
            elif operation == "get_orders":
                return await self._get_orders(data)
            else:
                # Стандартная логика
                return await self._standard_operation(data, operation)
                
        except Exception as e:
            logger.error(f"Ошибка синхронизации с ERP: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание счета в ERP"""
        mapped_data = self._map_fields(data, self.config.field_mapping)
        
        response = await self.client.post(
            "/invoices",
            json=mapped_data,
            headers=self.auth_headers
        )
        
        return {
            "success": response.status_code < 300,
            "data": response.json() if response.status_code < 300 else None,
            "error": response.text if response.status_code >= 300 else None
        }
    
    async def _update_inventory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление склада в ERP"""
        product_id = data.get("product_id")
        quantity = data.get("quantity")
        
        response = await self.client.patch(
            f"/inventory/{product_id}",
            json={"quantity": quantity},
            headers=self.auth_headers
        )
        
        return {
            "success": response.status_code < 300,
            "data": response.json() if response.status_code < 300 else None
        }
    
    async def _get_orders(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Получение заказов из ERP"""
        params = {}
        if "date_from" in filters:
            params["date_from"] = filters["date_from"]
        if "date_to" in filters:
            params["date_to"] = filters["date_to"]
        if "status" in filters:
            params["status"] = filters["status"]
        
        response = await self.client.get(
            "/orders",
            params=params,
            headers=self.auth_headers
        )
        
        return {
            "success": response.status_code < 300,
            "data": response.json() if response.status_code < 300 else None
        }
    
    async def _standard_operation(self, data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Стандартные операции"""
        # Реализация стандартных CRUD операций
        return {"success": False, "error": f"Операция {operation} не реализована"}


class RateLimiter:
    """Rate limiter для API запросов"""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Получение разрешения на запрос"""
        async with self.lock:
            now = datetime.utcnow()
            
            # Удаляем старые запросы
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < timedelta(minutes=1)
            ]
            
            # Проверяем лимит
            if len(self.requests) >= self.requests_per_minute:
                # Ждем до освобождения слота
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # Добавляем текущий запрос
            self.requests.append(now)


class ExternalAPIService:
    """Сервис для управления внешними API"""
    
    def __init__(self):
        self.connectors: Dict[int, BaseAPIConnector] = {}
        self.configs: Dict[int, ExternalAPIConfig] = {}
    
    async def register_api(self, config: ExternalAPIConfig, user_context: UserContext) -> int:
        """Регистрация внешнего API"""
        config_id = len(self.configs) + 1
        config.id = config_id
        
        # Создаем коннектор
        if "crm" in config.name.lower():
            connector = CRMConnector(config)
        elif "erp" in config.name.lower():
            connector = ERPConnector(config)
        else:
            # Используем базовый коннектор
            connector = CRMConnector(config)  # Временно используем CRM как базовый
        
        # Тестируем аутентификацию
        auth_success = await connector.authenticate()
        if not auth_success:
            raise ValueError("Ошибка аутентификации во внешнем API")
        
        # Тестируем подключение
        connection_test = await connector.test_connection()
        
        # Сохраняем конфигурацию
        self.configs[config_id] = config
        self.connectors[config_id] = connector
        
        # Логируем регистрацию
        AuditService.log_action(
            action=AuditAction.USER_CREATE,
            level=AuditLevel.INFO,
            user_context=user_context,
            resource_type="external_api",
            resource_id=str(config_id),
            details={
                "api_name": config.name,
                "api_type": config.api_type,
                "auth_success": auth_success,
                "connection_test": connection_test
            }
        )
        
        logger.info(f"API {config.name} зарегистрирован с ID {config_id}")
        return config_id
    
    async def sync_user_data(
        self,
        api_id: int,
        user_data: Dict[str, Any],
        operation: str,
        user_context: UserContext
    ) -> Dict[str, Any]:
        """Синхронизация пользовательских данных"""
        connector = self.connectors.get(api_id)
        if not connector:
            raise ValueError(f"API с ID {api_id} не найден")
        
        try:
            result = await connector.sync_data(user_data, operation)
            
            # Логируем синхронизацию
            AuditService.log_action(
                action=AuditAction.USER_UPDATE,
                level=AuditLevel.INFO,
                user_context=user_context,
                resource_type="external_sync",
                resource_id=str(api_id),
                success=result.get("success", False),
                details={
                    "operation": operation,
                    "api_name": connector.config.name,
                    "data_keys": list(user_data.keys())
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации с API {api_id}: {e}")
            
            AuditService.log_action(
                action=AuditAction.USER_UPDATE,
                level=AuditLevel.WARNING,
                user_context=user_context,
                resource_type="external_sync",
                resource_id=str(api_id),
                success=False,
                error_message=str(e)
            )
            
            raise
    
    async def sync_document_data(
        self,
        api_id: int,
        document_data: Dict[str, Any],
        user_context: UserContext
    ) -> Dict[str, Any]:
        """Синхронизация данных документов"""
        connector = self.connectors.get(api_id)
        if not connector:
            raise ValueError(f"API с ID {api_id} не найден")
        
        # Подготавливаем данные документа для внешней системы
        external_data = {
            "document_id": document_data.get("id"),
            "title": document_data.get("title"),
            "content_type": document_data.get("content_type"),
            "upload_date": document_data.get("created_at"),
            "uploaded_by": user_context.username,
            "tenant": user_context.tenant_id,
            "metadata": document_data.get("metadata", {})
        }
        
        result = await connector.sync_data(external_data, "create")
        
        # Логируем синхронизацию документа
        AuditService.log_action(
            action=AuditAction.DOCUMENT_UPLOAD,
            level=AuditLevel.INFO,
            user_context=user_context,
            resource_type="external_sync",
            resource_id=str(api_id),
            success=result.get("success", False),
            details={
                "document_id": document_data.get("id"),
                "api_name": connector.config.name,
                "sync_result": result.get("success", False)
            }
        )
        
        return result
    
    async def get_external_data(
        self,
        api_id: int,
        data_type: str,
        filters: Optional[Dict[str, Any]] = None,
        user_context: Optional[UserContext] = None
    ) -> Dict[str, Any]:
        """Получение данных из внешнего API"""
        connector = self.connectors.get(api_id)
        if not connector:
            raise ValueError(f"API с ID {api_id} не найден")
        
        try:
            if data_type == "orders":
                result = await connector.sync_data(filters or {}, "get_orders")
            elif data_type == "contacts":
                result = await connector.sync_data(filters or {}, "get")
            else:
                result = await connector.sync_data(filters or {}, f"get_{data_type}")
            
            if user_context:
                AuditService.log_action(
                    action=AuditAction.SEARCH_QUERY,
                    level=AuditLevel.INFO,
                    user_context=user_context,
                    resource_type="external_api",
                    resource_id=str(api_id),
                    details={
                        "data_type": data_type,
                        "filters": filters,
                        "success": result.get("success", False)
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения данных из API {api_id}: {e}")
            raise
    
    async def batch_sync(
        self,
        api_id: int,
        items: List[Dict[str, Any]],
        operation: str,
        user_context: UserContext,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Пакетная синхронизация данных"""
        connector = self.connectors.get(api_id)
        if not connector:
            raise ValueError(f"API с ID {api_id} не найден")
        
        results = []
        
        # Обрабатываем пакетами
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = []
            
            for item in batch:
                try:
                    result = await connector.sync_data(item, operation)
                    batch_results.append(result)
                except Exception as e:
                    batch_results.append({
                        "success": False,
                        "error": str(e),
                        "item": item
                    })
            
            results.extend(batch_results)
            
            # Небольшая пауза между пакетами
            await asyncio.sleep(0.1)
        
        # Логируем пакетную синхронизацию
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful
        
        AuditService.log_action(
            action=AuditAction.BULK_OPERATIONS,
            level=AuditLevel.INFO,
            user_context=user_context,
            resource_type="external_sync",
            resource_id=str(api_id),
            details={
                "operation": operation,
                "total_items": len(items),
                "successful": successful,
                "failed": failed,
                "batch_size": batch_size
            }
        )
        
        return results
    
    async def get_api_status(self, api_id: int) -> Dict[str, Any]:
        """Получение статуса API"""
        connector = self.connectors.get(api_id)
        config = self.configs.get(api_id)
        
        if not connector or not config:
            return {"status": "not_found"}
        
        # Тестируем подключение
        connection_ok = await connector.test_connection()
        
        return {
            "status": "active" if connection_ok else "error",
            "name": config.name,
            "type": config.api_type,
            "last_test": datetime.utcnow().isoformat(),
            "connection_ok": connection_ok
        }
    
    async def list_apis(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Получение списка API для тенанта"""
        apis = []
        
        for api_id, config in self.configs.items():
            if config.tenant_id == tenant_id:
                status = await self.get_api_status(api_id)
                apis.append({
                    "id": api_id,
                    "name": config.name,
                    "type": config.api_type,
                    "base_url": str(config.base_url),
                    "status": status["status"],
                    "active": config.active,
                    "created_at": config.created_at.isoformat()
                })
        
        return apis
    
    async def close_all_connections(self):
        """Закрытие всех подключений"""
        for connector in self.connectors.values():
            await connector.close()


# Глобальный экземпляр сервиса
external_api_service = ExternalAPIService()
