"""
Сервис для работы с webhooks и внешними интеграциями
"""
import asyncio
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import httpx
from fastapi import BackgroundTasks

from ..schemas.webhooks import (
    WebhookEndpoint, WebhookPayload, WebhookDelivery, WebhookEventType,
    WebhookStatus, WebhookDeliveryStatus, WebhookStats
)
from ..schemas.auth import UserContext
from ..services.audit import AuditService, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class WebhookService:
    """Сервис для управления webhooks"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.active_webhooks: Dict[int, WebhookEndpoint] = {}
        self.delivery_queue: asyncio.Queue = asyncio.Queue()
        
    async def register_webhook(
        self,
        endpoint: WebhookEndpoint,
        user_context: UserContext
    ) -> WebhookEndpoint:
        """
        Регистрация нового webhook
        
        Args:
            endpoint: Конфигурация webhook
            user_context: Контекст пользователя
            
        Returns:
            Созданный webhook endpoint
        """
        try:
            # Генерируем ID для webhook
            webhook_id = len(self.active_webhooks) + 1
            endpoint.id = webhook_id
            endpoint.created_by = user_context.user_id
            
            # Если не указан tenant_id, используем из контекста
            if endpoint.tenant_id is None:
                endpoint.tenant_id = user_context.tenant_id
            
            # Проверяем доступность URL
            test_result = await self._test_webhook_url(endpoint.url, endpoint.timeout_seconds)
            if not test_result:
                logger.warning(f"Webhook URL {endpoint.url} недоступен при регистрации")
            
            # Сохраняем webhook
            self.active_webhooks[webhook_id] = endpoint
            
            # TODO: Сохранить в базу данных
            
            # Логируем создание webhook
            AuditService.log_action(
                action=AuditAction.USER_CREATE,
                level=AuditLevel.INFO,
                user_context=user_context,
                resource_type="webhook",
                resource_id=str(webhook_id),
                details={
                    "webhook_name": endpoint.name,
                    "url": str(endpoint.url),
                    "events": [e.value for e in endpoint.events],
                    "test_result": test_result
                }
            )
            
            logger.info(f"Webhook {endpoint.name} зарегистрирован с ID {webhook_id}")
            return endpoint
            
        except Exception as e:
            logger.error(f"Ошибка регистрации webhook: {e}")
            
            AuditService.log_action(
                action=AuditAction.USER_CREATE,
                level=AuditLevel.WARNING,
                user_context=user_context,
                resource_type="webhook",
                success=False,
                error_message=str(e)
            )
            
            raise
    
    async def trigger_event(
        self,
        event_type: WebhookEventType,
        data: Dict[str, Any],
        user_context: Optional[UserContext] = None,
        tenant_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Отправка события в подписанные webhooks
        
        Args:
            event_type: Тип события
            data: Данные события
            user_context: Контекст пользователя
            tenant_id: ID тенанта
            metadata: Дополнительные метаданные
            
        Returns:
            Список ID отправленных событий
        """
        event_id = str(uuid.uuid4())
        sent_events = []
        
        # Создаем полезную нагрузку
        payload = WebhookPayload(
            event_type=event_type,
            event_id=event_id,
            tenant_id=tenant_id or (user_context.tenant_id if user_context else None),
            user_id=user_context.user_id if user_context else None,
            user_name=user_context.username if user_context else None,
            data=data,
            metadata=metadata or {}
        )
        
        # Находим подходящие webhooks
        target_webhooks = self._find_matching_webhooks(event_type, tenant_id, data)
        
        if not target_webhooks:
            logger.debug(f"Нет webhooks для события {event_type}")
            return sent_events
        
        # Отправляем в каждый webhook
        for webhook in target_webhooks:
            try:
                delivery = WebhookDelivery(
                    webhook_id=webhook.id,
                    event_id=event_id,
                    payload=payload,
                    max_attempts=webhook.max_retries
                )
                
                # Добавляем в очередь доставки
                await self.delivery_queue.put(delivery)
                sent_events.append(event_id)
                
                logger.debug(f"Событие {event_id} добавлено в очередь для webhook {webhook.name}")
                
            except Exception as e:
                logger.error(f"Ошибка добавления события в очередь для webhook {webhook.name}: {e}")
        
        # Логируем отправку события
        if user_context:
            AuditService.log_action(
                action=AuditAction.USER_UPDATE,  # Используем как webhook trigger
                level=AuditLevel.INFO,
                user_context=user_context,
                resource_type="webhook_event",
                resource_id=event_id,
                details={
                    "event_type": event_type,
                    "webhooks_count": len(target_webhooks),
                    "data_keys": list(data.keys())
                }
            )
        
        return sent_events
    
    def _find_matching_webhooks(
        self,
        event_type: WebhookEventType,
        tenant_id: Optional[int],
        data: Dict[str, Any]
    ) -> List[WebhookEndpoint]:
        """Поиск webhooks, подписанных на событие"""
        matching_webhooks = []
        
        for webhook in self.active_webhooks.values():
            # Проверяем активность
            if webhook.status != WebhookStatus.ACTIVE:
                continue
            
            # Проверяем подписку на событие
            if event_type not in webhook.events:
                continue
            
            # Проверяем тенант
            if webhook.tenant_id is not None and webhook.tenant_id != tenant_id:
                continue
            
            # Проверяем фильтры содержимого
            if webhook.content_filter and not self._matches_content_filter(data, webhook.content_filter):
                continue
            
            matching_webhooks.append(webhook)
        
        return matching_webhooks
    
    def _matches_content_filter(self, data: Dict[str, Any], content_filter: Dict[str, Any]) -> bool:
        """Проверка соответствия фильтру содержимого"""
        try:
            for key, expected_value in content_filter.items():
                if key not in data:
                    return False
                
                actual_value = data[key]
                
                # Простая проверка равенства
                if isinstance(expected_value, str) and expected_value.startswith("*"):
                    # Поддержка wildcards
                    pattern = expected_value[1:]
                    if pattern not in str(actual_value):
                        return False
                elif actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки фильтра содержимого: {e}")
            return False
    
    async def deliver_webhook(self, delivery: WebhookDelivery) -> bool:
        """
        Доставка webhook
        
        Args:
            delivery: Информация о доставке
            
        Returns:
            True если доставлен успешно
        """
        webhook = self.active_webhooks.get(delivery.webhook_id)
        if not webhook:
            logger.error(f"Webhook {delivery.webhook_id} не найден")
            return False
        
        delivery.attempt_count += 1
        delivery.sent_at = datetime.utcnow()
        
        try:
            # Подготавливаем данные
            payload_data = delivery.payload.dict()
            
            # Создаем подпись
            headers = {"Content-Type": "application/json"}
            if webhook.secret_token:
                signature = self._create_signature(payload_data, webhook.secret_token)
                headers["X-Webhook-Signature"] = signature
            
            # Отправляем запрос
            response = await self.client.post(
                str(webhook.url),
                json=payload_data,
                headers=headers,
                timeout=webhook.timeout_seconds
            )
            
            # Сохраняем результат
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Ограничиваем размер
            delivery.response_headers = dict(response.headers)
            
            if 200 <= response.status_code < 300:
                delivery.status = WebhookDeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
                
                # Обновляем статистику webhook
                webhook.last_delivery = datetime.utcnow()
                
                logger.info(f"Webhook {webhook.name} успешно доставлен")
                return True
            else:
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                
                logger.warning(f"Webhook {webhook.name} вернул статус {response.status_code}")
                return False
                
        except asyncio.TimeoutError:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error_message = f"Timeout после {webhook.timeout_seconds} секунд"
            logger.warning(f"Webhook {webhook.name} timeout")
            return False
            
        except Exception as e:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error_message = str(e)
            logger.error(f"Ошибка доставки webhook {webhook.name}: {e}")
            return False
        
        finally:
            # Планируем повторную попытку если нужно
            if (delivery.status == WebhookDeliveryStatus.FAILED and 
                delivery.attempt_count < delivery.max_attempts):
                
                delivery.status = WebhookDeliveryStatus.RETRYING
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=webhook.retry_delay_seconds)
                
                # Добавляем обратно в очередь с задержкой
                asyncio.create_task(self._schedule_retry(delivery, webhook.retry_delay_seconds))
                
            elif delivery.status == WebhookDeliveryStatus.FAILED:
                delivery.status = WebhookDeliveryStatus.EXPIRED
                logger.error(f"Webhook {webhook.name} исчерпал попытки доставки")
            
            # TODO: Сохранить результат в базу данных
    
    async def _schedule_retry(self, delivery: WebhookDelivery, delay_seconds: int):
        """Планирование повторной попытки доставки"""
        await asyncio.sleep(delay_seconds)
        await self.delivery_queue.put(delivery)
    
    def _create_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Создание подписи для webhook"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def _test_webhook_url(self, url: str, timeout: int) -> bool:
        """Тестирование доступности URL webhook"""
        try:
            response = await self.client.get(str(url), timeout=timeout)
            return response.status_code < 500
        except Exception:
            return False
    
    async def get_webhook_stats(self, webhook_id: int) -> Optional[WebhookStats]:
        """Получение статистики webhook"""
        # TODO: Получить статистику из базы данных
        webhook = self.active_webhooks.get(webhook_id)
        if not webhook:
            return None
        
        # Заглушка статистики
        return WebhookStats(
            webhook_id=webhook_id,
            total_deliveries=0,
            successful_deliveries=0,
            failed_deliveries=0,
            average_response_time_ms=0.0,
            last_delivery_at=webhook.last_delivery
        )
    
    async def deactivate_webhook(self, webhook_id: int, user_context: UserContext) -> bool:
        """Деактивация webhook"""
        webhook = self.active_webhooks.get(webhook_id)
        if not webhook:
            return False
        
        webhook.status = WebhookStatus.INACTIVE
        
        # Логируем деактивацию
        AuditService.log_action(
            action=AuditAction.USER_UPDATE,
            level=AuditLevel.INFO,
            user_context=user_context,
            resource_type="webhook",
            resource_id=str(webhook_id),
            details={"action": "deactivated", "webhook_name": webhook.name}
        )
        
        logger.info(f"Webhook {webhook.name} деактивирован")
        return True
    
    async def start_delivery_worker(self):
        """Запуск worker'а для обработки очереди доставки"""
        logger.info("Запуск webhook delivery worker")
        
        while True:
            try:
                # Получаем задачу из очереди
                delivery = await self.delivery_queue.get()
                
                # Обрабатываем доставку
                await self.deliver_webhook(delivery)
                
                # Отмечаем задачу как выполненную
                self.delivery_queue.task_done()
                
            except Exception as e:
                logger.error(f"Ошибка в webhook delivery worker: {e}")
                await asyncio.sleep(1)  # Небольшая пауза при ошибке


class EventTriggersHelper:
    """Помощник для trigger'ов событий"""
    
    def __init__(self, webhook_service: WebhookService):
        self.webhook_service = webhook_service
    
    async def document_uploaded(
        self,
        document_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        user_context: UserContext
    ):
        """Событие загрузки документа"""
        await self.webhook_service.trigger_event(
            event_type=WebhookEventType.DOCUMENT_UPLOADED,
            data={
                "document_id": document_id,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "uploaded_by": user_context.username
            },
            user_context=user_context
        )
    
    async def document_processed(
        self,
        document_id: str,
        processing_time_seconds: float,
        chunks_created: int,
        embeddings_created: int,
        user_context: UserContext
    ):
        """Событие обработки документа"""
        await self.webhook_service.trigger_event(
            event_type=WebhookEventType.DOCUMENT_PROCESSED,
            data={
                "document_id": document_id,
                "processing_time_seconds": processing_time_seconds,
                "chunks_created": chunks_created,
                "embeddings_created": embeddings_created,
                "status": "completed"
            },
            user_context=user_context
        )
    
    async def rag_query_completed(
        self,
        query_id: str,
        question: str,
        answer: str,
        sources_count: int,
        processing_time_ms: float,
        user_context: UserContext
    ):
        """Событие завершения RAG запроса"""
        await self.webhook_service.trigger_event(
            event_type=WebhookEventType.RAG_QUERY_COMPLETED,
            data={
                "query_id": query_id,
                "question": question,
                "answer_length": len(answer),
                "sources_count": sources_count,
                "processing_time_ms": processing_time_ms,
                "quality_score": None  # TODO: Добавить оценку качества
            },
            user_context=user_context
        )
    
    async def security_violation(
        self,
        violation_type: str,
        severity: str,
        details: Dict[str, Any],
        user_context: Optional[UserContext] = None,
        tenant_id: Optional[int] = None
    ):
        """Событие нарушения безопасности"""
        await self.webhook_service.trigger_event(
            event_type=WebhookEventType.SECURITY_VIOLATION,
            data={
                "violation_type": violation_type,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details
            },
            user_context=user_context,
            tenant_id=tenant_id
        )
    
    async def system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str,
        system_metrics: Dict[str, Any],
        tenant_id: Optional[int] = None
    ):
        """Системное уведомление"""
        await self.webhook_service.trigger_event(
            event_type=WebhookEventType.SYSTEM_ALERT,
            data={
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "system_metrics": system_metrics,
                "requires_action": severity in ["high", "critical"]
            },
            tenant_id=tenant_id
        )


# Глобальный экземпляр сервиса
webhook_service = WebhookService()
event_triggers = EventTriggersHelper(webhook_service)