"""
Сервис аудита действий пользователей
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel

from ..schemas.auth import UserContext
from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuditAction(str, Enum):
    """Типы действий для аудита"""
    LOGIN = "login"
    LOGOUT = "logout"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_DELETE = "document_delete"
    SEARCH_QUERY = "search_query"
    RAG_QUERY = "rag_query"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_CHANGE = "role_change"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    FAILED_LOGIN = "failed_login"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SECURITY_VIOLATION = "security_violation"


class AuditLevel(str, Enum):
    """Уровни важности аудита"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY = "security"


class AuditEntry(BaseModel):
    """Запись аудита"""
    id: Optional[int] = None
    timestamp: datetime
    user_id: Optional[int]
    username: Optional[str]
    tenant_id: Optional[int]
    action: AuditAction
    level: AuditLevel
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditService:
    """Сервис для аудита действий пользователей"""
    
    @staticmethod
    def log_action(
        action: AuditAction,
        level: AuditLevel = AuditLevel.INFO,
        user_context: Optional[UserContext] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditEntry:
        """
        Логирование действия пользователя
        
        Args:
            action: Тип действия
            level: Уровень важности
            user_context: Контекст пользователя
            resource_type: Тип ресурса
            resource_id: ID ресурса
            details: Дополнительные детали
            ip_address: IP адрес
            user_agent: User-Agent
            session_id: ID сессии
            success: Успешность операции
            error_message: Сообщение об ошибке
            
        Returns:
            Созданная запись аудита
        """
        
        # Создаем запись аудита
        audit_entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id=user_context.user_id if user_context else None,
            username=user_context.username if user_context else None,
            tenant_id=user_context.tenant_id if user_context else None,
            action=action,
            level=level,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            success=success,
            error_message=error_message
        )
        
        # Логируем в основной лог
        log_message = AuditService._format_log_message(audit_entry)
        
        if level == AuditLevel.CRITICAL or level == AuditLevel.SECURITY:
            logger.critical(log_message)
        elif level == AuditLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # TODO: Сохранить в базу данных для долгосрочного хранения
        # AuditService._save_to_database(audit_entry)
        
        # TODO: Отправить критические события в систему мониторинга
        if level in [AuditLevel.CRITICAL, AuditLevel.SECURITY]:
            AuditService._send_security_alert(audit_entry)
        
        return audit_entry
    
    @staticmethod
    def _format_log_message(entry: AuditEntry) -> str:
        """Форматирование сообщения для лога"""
        user_info = f"User: {entry.username}({entry.user_id})" if entry.username else "Anonymous"
        tenant_info = f"Tenant: {entry.tenant_id}" if entry.tenant_id else ""
        resource_info = f"Resource: {entry.resource_type}:{entry.resource_id}" if entry.resource_type else ""
        status = "SUCCESS" if entry.success else "FAILED"
        
        parts = [
            f"[{entry.level.upper()}]",
            f"Action: {entry.action}",
            user_info,
            tenant_info,
            resource_info,
            f"Status: {status}",
            f"IP: {entry.ip_address}" if entry.ip_address else "",
            f"Session: {entry.session_id}" if entry.session_id else ""
        ]
        
        # Убираем пустые части
        parts = [part for part in parts if part]
        
        message = " | ".join(parts)
        
        if entry.error_message:
            message += f" | Error: {entry.error_message}"
        
        if entry.details:
            message += f" | Details: {json.dumps(entry.details, ensure_ascii=False)}"
        
        return message
    
    @staticmethod
    def _send_security_alert(entry: AuditEntry):
        """Отправка уведомления о критическом событии безопасности"""
        # TODO: Интеграция с системой уведомлений
        logger.critical(f"🚨 SECURITY ALERT: {entry.action} - {entry.error_message}")
        
        # Примеры уведомлений:
        # - Email администраторам
        # - Slack/Teams уведомления
        # - Push в систему мониторинга (Prometheus/Grafana)
        # - Создание тикета в системе управления инцидентами
    
    @staticmethod
    def log_login_success(user_context: UserContext, ip_address: str, user_agent: str, session_id: str):
        """Логирование успешного входа"""
        AuditService.log_action(
            action=AuditAction.LOGIN,
            level=AuditLevel.INFO,
            user_context=user_context,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            details={"login_time": datetime.utcnow().isoformat()}
        )
    
    @staticmethod
    def log_login_failure(username: str, ip_address: str, user_agent: str, reason: str):
        """Логирование неудачного входа"""
        AuditService.log_action(
            action=AuditAction.FAILED_LOGIN,
            level=AuditLevel.WARNING,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=reason,
            details={"attempted_username": username}
        )
    
    @staticmethod
    def log_document_access(user_context: UserContext, document_id: str, action: AuditAction, 
                          ip_address: str, success: bool = True, error: str = None):
        """Логирование доступа к документу"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        AuditService.log_action(
            action=action,
            level=level,
            user_context=user_context,
            resource_type="document",
            resource_id=document_id,
            ip_address=ip_address,
            success=success,
            error_message=error
        )
    
    @staticmethod
    def log_search_query(user_context: UserContext, query: str, results_count: int, 
                        ip_address: str, response_time_ms: float):
        """Логирование поискового запроса"""
        AuditService.log_action(
            action=AuditAction.SEARCH_QUERY,
            level=AuditLevel.INFO,
            user_context=user_context,
            ip_address=ip_address,
            details={
                "query": query,
                "results_count": results_count,
                "response_time_ms": response_time_ms
            }
        )
    
    @staticmethod
    def log_rag_query(user_context: UserContext, question: str, answer_length: int,
                     sources_count: int, ip_address: str, response_time_ms: float):
        """Логирование RAG запроса"""
        AuditService.log_action(
            action=AuditAction.RAG_QUERY,
            level=AuditLevel.INFO,
            user_context=user_context,
            ip_address=ip_address,
            details={
                "question": question,
                "answer_length": answer_length,
                "sources_count": sources_count,
                "response_time_ms": response_time_ms
            }
        )
    
    @staticmethod
    def log_unauthorized_access(attempted_action: str, resource: str, user_context: Optional[UserContext],
                              ip_address: str, user_agent: str):
        """Логирование попытки неавторизованного доступа"""
        AuditService.log_action(
            action=AuditAction.UNAUTHORIZED_ACCESS,
            level=AuditLevel.SECURITY,
            user_context=user_context,
            resource_type=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=f"Unauthorized attempt to {attempted_action}",
            details={"attempted_action": attempted_action}
        )
    
    @staticmethod
    def log_permission_change(admin_context: UserContext, target_user_id: int, 
                            old_permissions: List[str], new_permissions: List[str], ip_address: str):
        """Логирование изменения разрешений"""
        AuditService.log_action(
            action=AuditAction.PERMISSION_GRANT if len(new_permissions) > len(old_permissions) else AuditAction.PERMISSION_REVOKE,
            level=AuditLevel.CRITICAL,
            user_context=admin_context,
            resource_type="user",
            resource_id=str(target_user_id),
            ip_address=ip_address,
            details={
                "old_permissions": old_permissions,
                "new_permissions": new_permissions,
                "changed_by_admin": admin_context.username
            }
        )


class AuditFilter:
    """Фильтры для поиска в аудите"""
    
    def __init__(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        actions: Optional[List[AuditAction]] = None,
        levels: Optional[List[AuditLevel]] = None,
        resource_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        success_only: Optional[bool] = None
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.actions = actions
        self.levels = levels
        self.resource_type = resource_type
        self.ip_address = ip_address
        self.success_only = success_only


# Middleware для автоматического аудита HTTP запросов
class AuditMiddleware:
    """Middleware для автоматического аудита HTTP запросов"""
    
    @staticmethod
    def get_client_ip(request) -> str:
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
    
    @staticmethod
    def get_user_agent(request) -> str:
        """Получение User-Agent"""
        return request.headers.get("User-Agent", "unknown")
