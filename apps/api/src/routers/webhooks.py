"""
Роутер для webhook интеграций
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import time
import hashlib
import hmac

from ..schemas.webhooks import (
    WebhookPayload,
    WebhookResponse,
    WebhookEvent,
    WebhookDelivery
)
from ..services.webhook_service import WebhookService
from ..services.authorization import get_current_user, User
from ..settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Инициализация сервисов
webhook_service = WebhookService()
settings = get_settings()

def verify_webhook_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_hub_signature: Optional[str] = Header(None)
) -> bool:
    """
    Проверка подписи webhook для безопасности
    
    Поддерживает:
    - GitHub-style HMAC SHA256
    - Старый формат HMAC SHA1
    """
    try:
        # Получаем тело запроса
        body = request.body()
        
        # Проверяем подпись SHA256 (приоритет)
        if x_hub_signature_256:
            expected_signature = f"sha256={hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()}"
            if hmac.compare_digest(x_hub_signature_256, expected_signature):
                return True
        
        # Проверяем подпись SHA1 (fallback)
        if x_hub_signature:
            expected_signature = f"sha1={hmac.new(settings.webhook_secret.encode(), body, hashlib.sha1).hexdigest()}"
            if hmac.compare_digest(x_hub_signature, expected_signature):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка проверки подписи webhook: {e}")
        return False

@router.post("/ingest", response_model=WebhookResponse)
async def webhook_ingest(
    request: Request,
    payload: WebhookPayload,
    x_hub_signature_256: Optional[str] = Header(None),
    x_hub_signature: Optional[str] = Header(None)
):
    """
    Webhook для запуска обработки документов
    
    Поддерживает:
    - GitHub webhooks
    - GitLab webhooks
    - Кастомные интеграции
    - Безопасность через HMAC подписи
    """
    try:
        start_time = time.time()
        
        # Проверяем подпись для безопасности
        if not verify_webhook_signature(request, x_hub_signature_256, x_hub_signature):
            logger.warning("❌ Неверная подпись webhook")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized webhook signature"
            )
        
        logger.info(f"🔗 Webhook ingest: {payload.event_type} от {payload.source}")
        
        # Обрабатываем webhook
        result = await webhook_service.process_ingest_webhook(
            payload=payload
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Webhook обработан за {processing_time:.3f}s")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки webhook: {str(e)}"
        )

@router.post("/airflow", response_model=WebhookResponse)
async def webhook_airflow(
    request: Request,
    payload: WebhookPayload,
    x_hub_signature_256: Optional[str] = Header(None),
    x_hub_signature: Optional[str] = Header(None)
):
    """
    Webhook для интеграции с Airflow
    
    Запускает:
    - DAG для обработки документов
    - DAG для синхронизации метрик
    - DAG для технического обслуживания
    """
    try:
        # Проверяем подпись
        if not verify_webhook_signature(request, x_hub_signature_256, x_hub_signature):
            logger.warning("❌ Неверная подпись webhook Airflow")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized webhook signature"
            )
        
        logger.info(f"🔄 Webhook Airflow: {payload.event_type}")
        
        # Обрабатываем webhook Airflow
        result = await webhook_service.process_airflow_webhook(
            payload=payload
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка webhook Airflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка webhook Airflow: {str(e)}"
        )

@router.post("/external", response_model=WebhookResponse)
async def webhook_external(
    request: Request,
    payload: WebhookPayload,
    x_hub_signature_256: Optional[str] = Header(None),
    x_hub_signature: Optional[str] = Header(None)
):
    """
    Webhook для внешних систем
    
    Поддерживает:
    - CRM системы
    - Helpdesk системы
    - Мониторинг
    - Алерты
    """
    try:
        # Проверяем подпись
        if not verify_webhook_signature(request, x_hub_signature_256, x_hub_signature):
            logger.warning("❌ Неверная подпись внешнего webhook")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized webhook signature"
            )
        
        logger.info(f"🌐 Внешний webhook: {payload.event_type} от {payload.source}")
        
        # Обрабатываем внешний webhook
        result = await webhook_service.process_external_webhook(
            payload=payload
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка внешнего webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка внешнего webhook: {str(e)}"
        )

@router.get("/events", response_model=List[WebhookEvent])
async def list_webhook_events(
    current_user: User = Depends(get_current_user),
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Список webhook событий
    
    Возвращает:
    - Историю webhook вызовов
    - Статусы обработки
    - Детали событий
    """
    try:
        logger.info(f"📋 Список webhook событий для пользователя {current_user.email}")
        
        events = await webhook_service.list_webhook_events(
            user=current_user,
            source=source,
            event_type=event_type,
            limit=limit,
            offset=offset
        )
        
        return events
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения webhook событий: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения webhook событий: {str(e)}"
        )

@router.get("/events/{event_id}", response_model=WebhookEvent)
async def get_webhook_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Детали webhook события
    
    Возвращает:
    - Полную информацию о событии
    - Payload
    - Статус обработки
    - Ошибки (если есть)
    """
    try:
        logger.info(f"📖 Детали webhook события {event_id}")
        
        event = await webhook_service.get_webhook_event(
            event_id=event_id,
            user=current_user
        )
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail="Webhook событие не найдено"
            )
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения webhook события: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения webhook события: {str(e)}"
        )

@router.post("/events/{event_id}/retry")
async def retry_webhook_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Повторная обработка webhook события
    
    Полезно при:
    - Ошибках обработки
    - Проблемах с внешними системами
    - Тестировании
    """
    try:
        logger.info(f"🔄 Повторная обработка webhook события {event_id}")
        
        result = await webhook_service.retry_webhook_event(
            event_id=event_id,
            user=current_user
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка повторной обработки: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка повторной обработки: {str(e)}"
        )

@router.get("/deliveries", response_model=List[WebhookDelivery])
async def list_webhook_deliveries(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Список доставок webhook
    
    Возвращает:
    - Статусы доставки
    - Попытки доставки
    - Ошибки доставки
    """
    try:
        logger.info(f"📤 Список доставок webhook для пользователя {current_user.email}")
        
        deliveries = await webhook_service.list_webhook_deliveries(
            user=current_user,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return deliveries
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения доставок webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения доставок: {str(e)}"
        )

@router.post("/test")
async def test_webhook(
    webhook_url: str,
    event_type: str = "test",
    payload: Optional[Dict[str, Any]] = None
):
    """
    Тестирование webhook
    
    Отправляет тестовое событие для проверки:
    - Доступности endpoint
    - Обработки payload
    - Ответа системы
    """
    try:
        logger.info(f"🧪 Тестирование webhook: {webhook_url}")
        
        # Создаем тестовый payload
        test_payload = payload or {
            "event_type": event_type,
            "source": "rag-platform",
            "timestamp": time.time(),
            "data": {
                "message": "Test webhook event",
                "test_id": f"test_{int(time.time())}"
            }
        }
        
        # Отправляем тестовый webhook
        result = await webhook_service.test_webhook(
            webhook_url=webhook_url,
            payload=test_payload
        )
        
        return {
            "message": "Webhook тест выполнен",
            "webhook_url": webhook_url,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка тестирования webhook: {str(e)}"
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_webhook_statistics(
    period: str = "7d",
    current_user: User = Depends(get_current_user)
):
    """
    Статистика webhook
    
    Возвращает:
    - Количество событий
    - Успешность обработки
    - Популярные источники
    - Время отклика
    """
    try:
        logger.info(f"📊 Статистика webhook за период {period}")
        
        stats = await webhook_service.get_webhook_statistics(
            period=period,
            user=current_user
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения статистики: {str(e)}"
        )

@router.post("/configure")
async def configure_webhook(
    webhook_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Настройка webhook
    
    Позволяет:
    - Добавить новые webhook endpoints
    - Настроить события
    - Установить секреты
    - Настроить retry логику
    """
    try:
        logger.info(f"⚙️ Настройка webhook для пользователя {current_user.email}")
        
        result = await webhook_service.configure_webhook(
            config=webhook_config,
            user=current_user
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка настройки webhook: {str(e)}"
        )

@router.delete("/configure/{webhook_id}")
async def delete_webhook_config(
    webhook_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Удаление конфигурации webhook
    
    Удаляет:
    - Webhook endpoint
    - Настройки событий
    - Секреты
    """
    try:
        logger.info(f"🗑️ Удаление webhook конфигурации {webhook_id}")
        
        await webhook_service.delete_webhook_config(
            webhook_id=webhook_id,
            user=current_user
        )
        
        return {"message": "Webhook конфигурация удалена"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления webhook конфигурации: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления webhook конфигурации: {str(e)}"
        )
