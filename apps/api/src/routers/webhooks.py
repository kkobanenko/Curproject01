"""
Роутер для управления webhooks и внешними интеграциями
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from typing import List, Optional
import logging

from ..schemas.webhooks import (
    WebhookEndpoint, WebhookCreate, WebhookUpdate, WebhookStats,
    WebhookPayload, WebhookEventType, DataExportRequest, DataExportJob
)
from ..schemas.auth import User, Permission
from ..schemas.common import PaginatedResponse, PaginationParams
from ..middleware.auth import get_current_user, require_permissions
from ..services.webhook_service import webhook_service, event_triggers
from ..services.audit import AuditService, AuditAction, AuditLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks и интеграции"])


@router.post("/", response_model=WebhookEndpoint)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN, Permission.USER_MANAGEMENT]))
):
    """
    Создание нового webhook
    
    Требуемые разрешения: ADMIN или USER_MANAGEMENT
    """
    try:
        webhook = WebhookEndpoint(
            name=webhook_data.name,
            url=webhook_data.url,
            events=webhook_data.events,
            active=webhook_data.active,
            secret_token=webhook_data.secret_token,
            timeout_seconds=webhook_data.timeout_seconds,
            max_retries=webhook_data.max_retries,
            retry_delay_seconds=webhook_data.retry_delay_seconds,
            tenant_id=webhook_data.tenant_id or current_user.tenant_id,
            user_filter=webhook_data.user_filter,
            content_filter=webhook_data.content_filter
        )
        
        created_webhook = await webhook_service.register_webhook(webhook, current_user)
        
        return created_webhook
        
    except Exception as e:
        logger.error(f"Ошибка создания webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания webhook: {str(e)}"
        )


@router.get("/", response_model=List[WebhookEndpoint])
async def list_webhooks(
    active_only: bool = True,
    event_type: Optional[WebhookEventType] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.READ, Permission.ADMIN]))
):
    """
    Получение списка webhooks
    
    Args:
        active_only: Только активные webhooks
        event_type: Фильтр по типу события
        
    Требуемые разрешения: READ или ADMIN
    """
    try:
        # Получаем webhooks из сервиса
        all_webhooks = list(webhook_service.active_webhooks.values())
        
        # Фильтруем по тенанту
        user_webhooks = [
            w for w in all_webhooks 
            if w.tenant_id is None or w.tenant_id == current_user.tenant_id
        ]
        
        # Применяем фильтры
        if active_only:
            user_webhooks = [w for w in user_webhooks if w.active]
            
        if event_type:
            user_webhooks = [w for w in user_webhooks if event_type in w.events]
        
        return user_webhooks
        
    except Exception as e:
        logger.error(f"Ошибка получения списка webhooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка webhooks"
        )


@router.get("/{webhook_id}", response_model=WebhookEndpoint)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.READ]))
):
    """Получение webhook по ID"""
    webhook = webhook_service.active_webhooks.get(webhook_id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook не найден"
        )
    
    # Проверяем доступ к тенанту
    if webhook.tenant_id and webhook.tenant_id != current_user.tenant_id:
        if Permission.ADMIN not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к webhook другого тенанта"
            )
    
    return webhook


@router.put("/{webhook_id}", response_model=WebhookEndpoint)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.WRITE, Permission.ADMIN]))
):
    """Обновление webhook"""
    webhook = webhook_service.active_webhooks.get(webhook_id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook не найден"
        )
    
    # Проверяем права доступа
    if webhook.tenant_id != current_user.tenant_id:
        if Permission.ADMIN not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на изменение webhook"
            )
    
    # Обновляем поля
    update_data = webhook_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    # Логируем обновление
    AuditService.log_action(
        action=AuditAction.USER_UPDATE,
        level=AuditLevel.INFO,
        user_context=current_user,
        resource_type="webhook",
        resource_id=str(webhook_id),
        details={"updated_fields": list(update_data.keys())}
    )
    
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.DELETE, Permission.ADMIN]))
):
    """Удаление webhook"""
    success = await webhook_service.deactivate_webhook(webhook_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook не найден"
        )
    
    return {"message": "Webhook удален"}


@router.get("/{webhook_id}/stats", response_model=WebhookStats)
async def get_webhook_stats(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.METRICS_VIEW]))
):
    """Получение статистики webhook"""
    stats = await webhook_service.get_webhook_stats(webhook_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook не найден"
        )
    
    return stats


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    test_payload: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.ADMIN]))
):
    """
    Тестирование webhook
    
    Отправляет тестовое событие в webhook
    """
    webhook = webhook_service.active_webhooks.get(webhook_id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook не найден"
        )
    
    # Создаем тестовое событие
    test_data = test_payload or {
        "test": True,
        "message": "Тестовое событие webhook",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    
    # Отправляем событие
    event_ids = await webhook_service.trigger_event(
        event_type=WebhookEventType.CUSTOM_EVENT,
        data=test_data,
        user_context=current_user,
        metadata={"test_mode": True}
    )
    
    return {
        "message": "Тестовое событие отправлено",
        "event_ids": event_ids
    }


@router.post("/trigger-event")
async def trigger_custom_event(
    event_data: dict,
    event_type: WebhookEventType = WebhookEventType.CUSTOM_EVENT,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.API_ACCESS]))
):
    """
    Ручной trigger события
    
    Позволяет отправить кастомное событие в webhooks
    """
    try:
        event_ids = await webhook_service.trigger_event(
            event_type=event_type,
            data=event_data,
            user_context=current_user
        )
        
        return {
            "message": f"Событие {event_type} отправлено",
            "event_ids": event_ids,
            "webhooks_notified": len(event_ids)
        }
        
    except Exception as e:
        logger.error(f"Ошибка отправки события: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка отправки события: {str(e)}"
        )


# Эндпоинты для экспорта данных
@router.post("/export", response_model=DataExportJob)
async def create_export_job(
    export_request: DataExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.EXPORT_DATA]))
):
    """
    Создание задачи экспорта данных
    
    Требуемые разрешения: EXPORT_DATA
    """
    try:
        # Создаем задачу экспорта
        job_id = f"export_{current_user.user_id}_{int(datetime.utcnow().timestamp())}"
        
        export_job = DataExportJob(
            id=job_id,
            request=export_request,
            status="created",
            created_by=current_user.user_id
        )
        
        # Запускаем экспорт в фоне
        background_tasks.add_task(
            _process_export_job,
            export_job,
            current_user
        )
        
        # Логируем создание задачи экспорта
        AuditService.log_action(
            action=AuditAction.EXPORT_DATA,
            level=AuditLevel.INFO,
            user_context=current_user,
            resource_type="export_job",
            resource_id=job_id,
            details={
                "export_type": export_request.export_type,
                "format": export_request.format,
                "max_records": export_request.max_records
            }
        )
        
        return export_job
        
    except Exception as e:
        logger.error(f"Ошибка создания задачи экспорта: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания задачи экспорта: {str(e)}"
        )


@router.get("/export/{job_id}", response_model=DataExportJob)
async def get_export_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions([Permission.EXPORT_DATA]))
):
    """Получение статуса задачи экспорта"""
    # TODO: Получить из базы данных или кэша
    # Пока возвращаем заглушку
    return DataExportJob(
        id=job_id,
        request=DataExportRequest(
            export_type="documents",
            format="json"
        ),
        status="completed",
        progress_percent=100.0,
        created_by=current_user.user_id,
        download_url=f"/api/v1/export/{job_id}/download"
    )


async def _process_export_job(export_job: DataExportJob, user_context: User):
    """Обработка задачи экспорта в фоне"""
    try:
        export_job.status = "processing"
        export_job.started_at = datetime.utcnow()
        
        # TODO: Реализовать логику экспорта данных
        # 1. Получить данные из БД согласно фильтрам
        # 2. Преобразовать в нужный формат
        # 3. Сохранить файл
        # 4. Создать download URL
        
        # Имитация обработки
        import asyncio
        await asyncio.sleep(2)
        
        export_job.status = "completed"
        export_job.completed_at = datetime.utcnow()
        export_job.progress_percent = 100.0
        export_job.records_processed = 100
        export_job.download_url = f"/api/v1/export/{export_job.id}/download"
        
        # Отправляем webhook о завершении экспорта
        await event_triggers.document_processed(
            document_id=export_job.id,
            processing_time_seconds=2.0,
            chunks_created=0,
            embeddings_created=0,
            user_context=user_context
        )
        
        logger.info(f"Экспорт {export_job.id} завершен")
        
    except Exception as e:
        export_job.status = "failed"
        export_job.error_message = str(e)
        
        logger.error(f"Ошибка обработки экспорта {export_job.id}: {e}")


# Вспомогательные эндпоинты
@router.get("/events/types")
async def get_event_types(
    current_user: User = Depends(get_current_user)
):
    """Получение списка доступных типов событий"""
    return {
        "event_types": [
            {
                "value": event.value,
                "description": _get_event_description(event)
            }
            for event in WebhookEventType
        ]
    }


def _get_event_description(event_type: WebhookEventType) -> str:
    """Получение описания типа события"""
    descriptions = {
        WebhookEventType.DOCUMENT_UPLOADED: "Документ загружен в систему",
        WebhookEventType.DOCUMENT_PROCESSED: "Документ обработан и проиндексирован",
        WebhookEventType.DOCUMENT_DELETED: "Документ удален из системы",
        WebhookEventType.DOCUMENT_SHARED: "Документ предоставлен в общий доступ",
        WebhookEventType.USER_REGISTERED: "Новый пользователь зарегистрирован",
        WebhookEventType.USER_LOGIN: "Пользователь вошел в систему",
        WebhookEventType.USER_UPDATED: "Данные пользователя обновлены",
        WebhookEventType.USER_DELETED: "Пользователь удален",
        WebhookEventType.RAG_QUERY_COMPLETED: "RAG запрос выполнен",
        WebhookEventType.SEARCH_PERFORMED: "Выполнен поиск по документам",
        WebhookEventType.SYSTEM_ALERT: "Системное уведомление",
        WebhookEventType.BACKUP_COMPLETED: "Резервное копирование завершено",
        WebhookEventType.MAINTENANCE_STARTED: "Начато техническое обслуживание",
        WebhookEventType.MAINTENANCE_COMPLETED: "Техническое обслуживание завершено",
        WebhookEventType.SECURITY_VIOLATION: "Нарушение безопасности",
        WebhookEventType.LOGIN_FAILED: "Неудачная попытка входа",
        WebhookEventType.PERMISSION_CHANGED: "Изменены разрешения пользователя",
        WebhookEventType.CUSTOM_EVENT: "Пользовательское событие"
    }
    
    return descriptions.get(event_type, "Неизвестное событие")