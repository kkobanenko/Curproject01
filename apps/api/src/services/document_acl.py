"""
Сервис управления правами доступа к документам (ACL)
"""
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import logging

from ..schemas.auth import UserContext, Permission, DocumentACL
from ..services.audit import AuditService, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Типы документов для ACL"""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    HTML = "html"
    EMAIL = "email"
    IMAGE = "image"
    TEXT = "text"
    OTHER = "other"


class DocumentClassification(str, Enum):
    """Классификация документов по безопасности"""
    PUBLIC = "public"          # Доступны всем в тенанте
    INTERNAL = "internal"      # Доступны сотрудникам
    CONFIDENTIAL = "confidential"  # Доступны определенным ролям
    RESTRICTED = "restricted"  # Доступны только определенным пользователям
    SECRET = "secret"         # Максимальные ограничения доступа


class DocumentACLService:
    """Сервис управления правами доступа к документам"""
    
    @staticmethod
    def check_document_access(
        user_context: UserContext,
        document_id: str,
        required_permission: Permission,
        document_tenant_id: int,
        document_classification: DocumentClassification = DocumentClassification.INTERNAL,
        document_acl: Optional[List[DocumentACL]] = None
    ) -> bool:
        """
        Проверка доступа пользователя к документу
        
        Args:
            user_context: Контекст пользователя
            document_id: ID документа
            required_permission: Требуемое разрешение
            document_tenant_id: ID тенанта документа
            document_classification: Классификация безопасности
            document_acl: Список ACL для документа
            
        Returns:
            True если доступ разрешен
        """
        
        # Суперадминистраторы имеют доступ ко всему
        if user_context.is_admin and Permission.ADMIN in user_context.permissions:
            return True
        
        # Проверяем принадлежность к тенанту
        if user_context.tenant_id != document_tenant_id:
            logger.warning(f"Пользователь {user_context.username} пытается получить доступ к документу {document_id} из другого тенанта")
            return False
        
        # Проверяем классификацию безопасности
        if not DocumentACLService._check_classification_access(user_context, document_classification):
            return False
        
        # Проверяем специфические ACL правила для документа
        if document_acl:
            return DocumentACLService._check_document_acl(user_context, document_acl, required_permission)
        
        # Проверяем базовые разрешения пользователя
        return DocumentACLService._check_basic_permissions(user_context, required_permission)
    
    @staticmethod
    def _check_classification_access(user_context: UserContext, classification: DocumentClassification) -> bool:
        """Проверка доступа на основе классификации документа"""
        
        if classification == DocumentClassification.PUBLIC:
            return True
        
        if classification == DocumentClassification.INTERNAL:
            # Все аутентифицированные пользователи тенанта
            return Permission.READ in user_context.permissions
        
        if classification == DocumentClassification.CONFIDENTIAL:
            # Только пользователи с специальными разрешениями
            required_permissions = {Permission.READ, Permission.WRITE}
            return bool(set(user_context.permissions).intersection(required_permissions))
        
        if classification == DocumentClassification.RESTRICTED:
            # Только администраторы и пользователи с админскими правами
            admin_permissions = {Permission.ADMIN, Permission.USER_MANAGEMENT}
            return bool(set(user_context.permissions).intersection(admin_permissions))
        
        if classification == DocumentClassification.SECRET:
            # Только полные администраторы
            return Permission.ADMIN in user_context.permissions
        
        return False
    
    @staticmethod
    def _check_document_acl(user_context: UserContext, document_acl: List[DocumentACL], 
                          required_permission: Permission) -> bool:
        """Проверка ACL правил для конкретного документа"""
        
        # Проверяем прямые разрешения пользователя
        for acl in document_acl:
            if acl.user_id == user_context.user_id:
                return required_permission in acl.permissions
        
        # Проверяем разрешения роли
        for acl in document_acl:
            if acl.role_id == user_context.role_id and acl.user_id is None:
                return required_permission in acl.permissions
        
        # Проверяем общие разрешения тенанта
        for acl in document_acl:
            if acl.role_id is None and acl.user_id is None and acl.tenant_id == user_context.tenant_id:
                return required_permission in acl.permissions
        
        return False
    
    @staticmethod
    def _check_basic_permissions(user_context: UserContext, required_permission: Permission) -> bool:
        """Проверка базовых разрешений пользователя"""
        return required_permission in user_context.permissions
    
    @staticmethod
    def create_document_acl(
        document_id: str,
        tenant_id: int,
        creator_context: UserContext,
        classification: DocumentClassification = DocumentClassification.INTERNAL,
        additional_permissions: Optional[List[Dict[str, Any]]] = None
    ) -> List[DocumentACL]:
        """
        Создание ACL для нового документа
        
        Args:
            document_id: ID документа
            tenant_id: ID тенанта
            creator_context: Контекст создателя документа
            classification: Классификация безопасности
            additional_permissions: Дополнительные разрешения
            
        Returns:
            Список созданных ACL записей
        """
        
        acl_list = []
        
        # Создатель получает полные права
        creator_acl = DocumentACL(
            id=0,  # Будет установлен при сохранении в БД
            document_id=int(document_id),
            tenant_id=tenant_id,
            user_id=creator_context.user_id,
            permissions=[Permission.READ, Permission.WRITE, Permission.DELETE, Permission.SHARE],
            created_by=creator_context.user_id
        )
        acl_list.append(creator_acl)
        
        # Базовые разрешения в зависимости от классификации
        if classification == DocumentClassification.PUBLIC:
            # Все в тенанте могут читать
            public_acl = DocumentACL(
                id=0,
                document_id=int(document_id),
                tenant_id=tenant_id,
                permissions=[Permission.READ],
                created_by=creator_context.user_id
            )
            acl_list.append(public_acl)
        
        elif classification == DocumentClassification.INTERNAL:
            # Все сотрудники могут читать, некоторые - писать
            internal_read_acl = DocumentACL(
                id=0,
                document_id=int(document_id),
                tenant_id=tenant_id,
                permissions=[Permission.READ],
                created_by=creator_context.user_id
            )
            acl_list.append(internal_read_acl)
        
        # Добавляем дополнительные разрешения
        if additional_permissions:
            for perm in additional_permissions:
                additional_acl = DocumentACL(
                    id=0,
                    document_id=int(document_id),
                    tenant_id=tenant_id,
                    role_id=perm.get("role_id"),
                    user_id=perm.get("user_id"),
                    permissions=perm.get("permissions", [Permission.READ]),
                    created_by=creator_context.user_id
                )
                acl_list.append(additional_acl)
        
        # Логируем создание ACL
        AuditService.log_action(
            action=AuditAction.PERMISSION_GRANT,
            level=AuditLevel.INFO,
            user_context=creator_context,
            resource_type="document",
            resource_id=document_id,
            details={
                "classification": classification,
                "acl_count": len(acl_list),
                "permissions_granted": len(additional_permissions) if additional_permissions else 0
            }
        )
        
        return acl_list
    
    @staticmethod
    def update_document_permissions(
        document_id: str,
        user_context: UserContext,
        new_permissions: List[Dict[str, Any]],
        ip_address: str
    ) -> bool:
        """
        Обновление разрешений для документа
        
        Args:
            document_id: ID документа
            user_context: Контекст пользователя
            new_permissions: Новые разрешения
            ip_address: IP адрес пользователя
            
        Returns:
            True если успешно
        """
        
        # Проверяем права на изменение разрешений
        if not (Permission.ADMIN in user_context.permissions or 
                Permission.SHARE in user_context.permissions):
            AuditService.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                level=AuditLevel.SECURITY,
                user_context=user_context,
                resource_type="document",
                resource_id=document_id,
                ip_address=ip_address,
                success=False,
                error_message="Недостаточно прав для изменения разрешений документа"
            )
            return False
        
        try:
            # TODO: Реализовать обновление в базе данных
            
            # Логируем изменение разрешений
            AuditService.log_action(
                action=AuditAction.PERMISSION_GRANT,
                level=AuditLevel.CRITICAL,
                user_context=user_context,
                resource_type="document",
                resource_id=document_id,
                ip_address=ip_address,
                details={
                    "new_permissions_count": len(new_permissions),
                    "changed_by": user_context.username
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления разрешений для документа {document_id}: {e}")
            
            AuditService.log_action(
                action=AuditAction.PERMISSION_GRANT,
                level=AuditLevel.CRITICAL,
                user_context=user_context,
                resource_type="document",
                resource_id=document_id,
                ip_address=ip_address,
                success=False,
                error_message=str(e)
            )
            
            return False
    
    @staticmethod
    def get_user_accessible_documents(
        user_context: UserContext,
        document_type: Optional[DocumentType] = None,
        classification: Optional[DocumentClassification] = None
    ) -> List[str]:
        """
        Получение списка документов, доступных пользователю
        
        Args:
            user_context: Контекст пользователя
            document_type: Фильтр по типу документа
            classification: Фильтр по классификации
            
        Returns:
            Список ID документов
        """
        
        # TODO: Реализовать запрос к базе данных с учетом ACL
        # Пока возвращаем заглушку
        accessible_documents = []
        
        # Логируем запрос списка документов
        AuditService.log_action(
            action=AuditAction.DOCUMENT_VIEW,
            level=AuditLevel.INFO,
            user_context=user_context,
            details={
                "document_type_filter": document_type,
                "classification_filter": classification,
                "results_count": len(accessible_documents)
            }
        )
        
        return accessible_documents
    
    @staticmethod
    def filter_search_results_by_acl(
        user_context: UserContext,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация результатов поиска по правам доступа
        
        Args:
            user_context: Контекст пользователя
            search_results: Результаты поиска
            
        Returns:
            Отфильтрованные результаты
        """
        
        filtered_results = []
        
        for result in search_results:
            document_id = result.get("document_id")
            document_tenant_id = result.get("tenant_id", user_context.tenant_id)
            document_classification = DocumentClassification(
                result.get("classification", DocumentClassification.INTERNAL)
            )
            
            # Проверяем доступ к документу
            if DocumentACLService.check_document_access(
                user_context=user_context,
                document_id=str(document_id),
                required_permission=Permission.READ,
                document_tenant_id=document_tenant_id,
                document_classification=document_classification
            ):
                filtered_results.append(result)
        
        # Логируем фильтрацию результатов
        filtered_count = len(search_results) - len(filtered_results)
        if filtered_count > 0:
            AuditService.log_action(
                action=AuditAction.SEARCH_QUERY,
                level=AuditLevel.INFO,
                user_context=user_context,
                details={
                    "total_results": len(search_results),
                    "filtered_results": len(filtered_results),
                    "filtered_out": filtered_count
                }
            )
        
        return filtered_results
    
    @staticmethod
    def check_bulk_operation_permissions(
        user_context: UserContext,
        document_ids: List[str],
        required_permission: Permission
    ) -> Dict[str, bool]:
        """
        Проверка разрешений для массовых операций
        
        Args:
            user_context: Контекст пользователя
            document_ids: Список ID документов
            required_permission: Требуемое разрешение
            
        Returns:
            Словарь {document_id: has_permission}
        """
        
        # Проверяем разрешение на массовые операции
        if Permission.BULK_OPERATIONS not in user_context.permissions:
            AuditService.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                level=AuditLevel.WARNING,
                user_context=user_context,
                success=False,
                error_message="Нет разрешения на массовые операции",
                details={"attempted_documents": len(document_ids)}
            )
            return {doc_id: False for doc_id in document_ids}
        
        permissions_map = {}
        
        for document_id in document_ids:
            # TODO: Получить информацию о документе из БД
            # Пока используем заглушку
            has_permission = DocumentACLService.check_document_access(
                user_context=user_context,
                document_id=document_id,
                required_permission=required_permission,
                document_tenant_id=user_context.tenant_id
            )
            permissions_map[document_id] = has_permission
        
        # Логируем массовую проверку разрешений
        allowed_count = sum(permissions_map.values())
        AuditService.log_action(
            action=AuditAction.BULK_OPERATIONS,
            level=AuditLevel.INFO,
            user_context=user_context,
            details={
                "total_documents": len(document_ids),
                "allowed_documents": allowed_count,
                "denied_documents": len(document_ids) - allowed_count,
                "required_permission": required_permission
            }
        )
        
        return permissions_map


class TenantACLService:
    """Сервис управления правами доступа на уровне тенанта"""
    
    @staticmethod
    def check_tenant_access(user_context: UserContext, target_tenant_id: int) -> bool:
        """Проверка доступа к ресурсам тенанта"""
        
        # Суперадминистраторы могут работать с любыми тенантами
        if user_context.is_admin and Permission.ADMIN in user_context.permissions:
            return True
        
        # Обычные пользователи только в своем тенанте
        return user_context.tenant_id == target_tenant_id
    
    @staticmethod
    def get_tenant_permissions(user_context: UserContext) -> List[Permission]:
        """Получение разрешений пользователя в рамках тенанта"""
        
        # Базовые разрешения из контекста
        tenant_permissions = list(user_context.permissions)
        
        # TODO: Добавить проверку дополнительных разрешений из БД
        
        return tenant_permissions
    
    @staticmethod
    def check_cross_tenant_operation(
        user_context: UserContext,
        source_tenant_id: int,
        target_tenant_id: int,
        operation: str
    ) -> bool:
        """Проверка разрешения на межтенантные операции"""
        
        if source_tenant_id == target_tenant_id:
            return True
        
        # Только суперадминистраторы могут выполнять межтенантные операции
        if not (user_context.is_admin and Permission.ADMIN in user_context.permissions):
            AuditService.log_action(
                action=AuditAction.UNAUTHORIZED_ACCESS,
                level=AuditLevel.SECURITY,
                user_context=user_context,
                success=False,
                error_message=f"Попытка межтенантной операции: {operation}",
                details={
                    "source_tenant": source_tenant_id,
                    "target_tenant": target_tenant_id,
                    "operation": operation
                }
            )
            return False
        
        return True
