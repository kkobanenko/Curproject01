"""
Система алертов и уведомлений
"""
import asyncio
import logging
import smtplib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import clickhouse_connect
from ..settings.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AlertRule:
    """Правило для генерации алертов"""
    rule_id: str
    name: str
    description: str
    condition: str  # SQL условие
    severity: str  # info, warning, critical
    service: str
    enabled: bool = True
    cooldown_minutes: int = 15  # Минимальный интервал между алертами
    notification_channels: List[str] = None  # email, webhook, slack, etc.
    metadata: Dict[str, Any] = None


@dataclass
class Alert:
    """Алерт"""
    alert_id: str
    alert_type: str
    severity: str
    service: str
    message: str
    status: str  # active, resolved, acknowledged
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class NotificationChannel:
    """Канал уведомлений"""
    channel_id: str
    channel_type: str  # email, webhook, slack
    name: str
    enabled: bool = True
    config: Dict[str, Any] = None


class AlertSystem:
    """Система алертов и уведомлений"""
    
    def __init__(self):
        self.clickhouse_client = None
        self._initialize_clickhouse()
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.custom_handlers: Dict[str, Callable] = {}
        self._load_default_rules()
        self._load_default_channels()
    
    def _initialize_clickhouse(self):
        """Инициализация подключения к ClickHouse"""
        try:
            self.clickhouse_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DATABASE
            )
            logger.info("ClickHouse connection initialized for alert system")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse for alert system: {e}")
            self.clickhouse_client = None
    
    def _load_default_rules(self):
        """Загрузка правил алертов по умолчанию"""
        default_rules = [
            AlertRule(
                rule_id="high_cpu_usage",
                name="High CPU Usage",
                description="CPU usage exceeds 80%",
                condition="SELECT service, avg(cpu_usage_percent) as avg_cpu FROM rag.resource_usage_metrics WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY service HAVING avg_cpu > 80",
                severity="warning",
                service="*",
                cooldown_minutes=10,
                notification_channels=["email"]
            ),
            AlertRule(
                rule_id="high_memory_usage",
                name="High Memory Usage",
                description="Memory usage exceeds 85%",
                condition="SELECT service, avg(memory_usage_mb) as avg_memory FROM rag.resource_usage_metrics WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY service HAVING avg_memory > 1000",
                severity="warning",
                service="*",
                cooldown_minutes=10,
                notification_channels=["email"]
            ),
            AlertRule(
                rule_id="high_disk_usage",
                name="High Disk Usage",
                description="Disk usage exceeds 90%",
                condition="SELECT service, avg(disk_usage_mb) as avg_disk FROM rag.resource_usage_metrics WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY service HAVING avg_disk > 50000",
                severity="critical",
                service="*",
                cooldown_minutes=5,
                notification_channels=["email", "webhook"]
            ),
            AlertRule(
                rule_id="search_error_rate",
                name="High Search Error Rate",
                description="Search error rate exceeds 10%",
                condition="SELECT tenant_id, countIf(success = 0) * 100.0 / count() as error_rate FROM rag.search_metrics WHERE timestamp >= now() - INTERVAL 10 MINUTE GROUP BY tenant_id HAVING error_rate > 10",
                severity="warning",
                service="search",
                cooldown_minutes=15,
                notification_channels=["email"]
            ),
            AlertRule(
                rule_id="api_response_time",
                name="High API Response Time",
                description="API response time exceeds 5 seconds",
                condition="SELECT endpoint, avg(response_time_ms) as avg_response_time FROM rag.api_metrics WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY endpoint HAVING avg_response_time > 5000",
                severity="warning",
                service="api",
                cooldown_minutes=10,
                notification_channels=["email"]
            ),
            AlertRule(
                rule_id="embedding_failure_rate",
                name="High Embedding Failure Rate",
                description="Embedding failure rate exceeds 5%",
                condition="SELECT tenant_id, countIf(success = 0) * 100.0 / count() as failure_rate FROM rag.embedding_metrics WHERE timestamp >= now() - INTERVAL 10 MINUTE GROUP BY tenant_id HAVING failure_rate > 5",
                severity="warning",
                service="embedding",
                cooldown_minutes=15,
                notification_channels=["email"]
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    def _load_default_channels(self):
        """Загрузка каналов уведомлений по умолчанию"""
        default_channels = [
            NotificationChannel(
                channel_id="email_admin",
                channel_type="email",
                name="Admin Email",
                enabled=True,
                config={
                    "smtp_server": getattr(settings, 'SMTP_SERVER', 'localhost'),
                    "smtp_port": getattr(settings, 'SMTP_PORT', 587),
                    "username": getattr(settings, 'SMTP_USERNAME', ''),
                    "password": getattr(settings, 'SMTP_PASSWORD', ''),
                    "from_email": getattr(settings, 'SMTP_FROM_EMAIL', 'alerts@rag-system.com'),
                    "to_emails": getattr(settings, 'ALERT_EMAILS', ['admin@rag-system.com']).split(',')
                }
            ),
            NotificationChannel(
                channel_id="webhook_slack",
                channel_type="webhook",
                name="Slack Webhook",
                enabled=False,
                config={
                    "url": getattr(settings, 'SLACK_WEBHOOK_URL', ''),
                    "channel": getattr(settings, 'SLACK_CHANNEL', '#alerts')
                }
            )
        ]
        
        for channel in default_channels:
            self.notification_channels[channel.channel_id] = channel
    
    async def check_alert_rules(self):
        """Проверка всех правил алертов"""
        if not self.clickhouse_client:
            logger.warning("ClickHouse client not available for alert checking")
            return
        
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Проверка кулдауна
            if self._is_in_cooldown(rule_id):
                continue
            
            try:
                # Выполнение условия правила
                result = self.clickhouse_client.query(rule.condition)
                
                if result.result_rows:
                    # Создание алертов для каждой строки результата
                    for row in result.result_rows:
                        await self._create_alert(rule, row)
                        
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_id}: {e}")
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Проверка кулдауна для правила"""
        if rule_id not in self.alert_cooldowns:
            return False
        
        rule = self.alert_rules.get(rule_id)
        if not rule:
            return False
        
        cooldown_end = self.alert_cooldowns[rule_id] + timedelta(minutes=rule.cooldown_minutes)
        return datetime.now(timezone.utc) < cooldown_end
    
    async def _create_alert(self, rule: AlertRule, data: List[Any]):
        """Создание алерта на основе правила"""
        try:
            alert_id = f"{rule.rule_id}_{int(datetime.now().timestamp())}"
            
            # Формирование сообщения
            message = f"{rule.name}: {rule.description}"
            if len(data) > 1:
                message += f" (Current value: {data[1]})"
            
            alert = Alert(
                alert_id=alert_id,
                alert_type=rule.rule_id,
                severity=rule.severity,
                service=rule.service,
                message=message,
                status="active",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "rule_id": rule.rule_id,
                    "data": data,
                    "condition": rule.condition
                }
            )
            
            # Сохранение алерта
            await self._store_alert(alert)
            
            # Отправка уведомлений
            await self._send_notifications(alert, rule.notification_channels)
            
            # Установка кулдауна
            self.alert_cooldowns[rule.rule_id] = datetime.now(timezone.utc)
            
            logger.info(f"Created alert: {alert_id} - {message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _store_alert(self, alert: Alert):
        """Сохранение алерта в ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            alert_data = {
                'timestamp': alert.timestamp,
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'service': alert.service,
                'message': alert.message,
                'status': alert.status,
                'resolved_at': alert.resolved_at,
                'metadata': alert.metadata or {}
            }
            
            self.clickhouse_client.insert(
                'rag.alerts',
                [alert_data]
            )
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    async def _send_notifications(self, alert: Alert, channels: List[str]):
        """Отправка уведомлений по каналам"""
        for channel_id in channels:
            channel = self.notification_channels.get(channel_id)
            if not channel or not channel.enabled:
                continue
            
            try:
                if channel.channel_type == "email":
                    await self._send_email_notification(alert, channel)
                elif channel.channel_type == "webhook":
                    await self._send_webhook_notification(alert, channel)
                elif channel.channel_type == "slack":
                    await self._send_slack_notification(alert, channel)
                elif channel_id in self.custom_handlers:
                    await self.custom_handlers[channel_id](alert, channel)
                    
            except Exception as e:
                logger.error(f"Error sending notification via {channel_id}: {e}")
    
    async def _send_email_notification(self, alert: Alert, channel: NotificationChannel):
        """Отправка email уведомления"""
        try:
            config = channel.config
            
            # Создание сообщения
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.service} - {alert.alert_type}"
            
            # Тело сообщения
            body = f"""
Alert Details:
- ID: {alert.alert_id}
- Type: {alert.alert_type}
- Severity: {alert.severity}
- Service: {alert.service}
- Message: {alert.message}
- Timestamp: {alert.timestamp}
- Status: {alert.status}

Metadata:
{json.dumps(alert.metadata, indent=2) if alert.metadata else 'None'}

This is an automated alert from the RAG System monitoring.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Отправка
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            if config.get('username') and config.get('password'):
                server.starttls()
                server.login(config['username'], config['password'])
            
            text = msg.as_string()
            server.sendmail(config['from_email'], config['to_emails'], text)
            server.quit()
            
            logger.info(f"Email notification sent for alert {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    async def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel):
        """Отправка webhook уведомления"""
        try:
            import aiohttp
            
            config = channel.config
            webhook_data = {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "service": alert.service,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status,
                "metadata": alert.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['url'],
                    json=webhook_data,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent for alert {alert.alert_id}")
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    async def _send_slack_notification(self, alert: Alert, channel: NotificationChannel):
        """Отправка Slack уведомления"""
        try:
            import aiohttp
            
            config = channel.config
            
            # Форматирование сообщения для Slack
            color = {
                'info': '#36a64f',
                'warning': '#ff9500',
                'critical': '#ff0000'
            }.get(alert.severity, '#36a64f')
            
            slack_data = {
                "channel": config['channel'],
                "attachments": [{
                    "color": color,
                    "title": f"Alert: {alert.alert_type}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Service", "value": alert.service, "short": True},
                        {"title": "Severity", "value": alert.severity, "short": True},
                        {"title": "Status", "value": alert.status, "short": True},
                        {"title": "Timestamp", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True}
                    ],
                    "footer": "RAG System Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['url'],
                    json=slack_data,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for alert {alert.alert_id}")
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def add_alert_rule(self, rule: AlertRule):
        """Добавление нового правила алерта"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.rule_id}")
    
    def remove_alert_rule(self, rule_id: str):
        """Удаление правила алерта"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Добавление нового канала уведомлений"""
        self.notification_channels[channel.channel_id] = channel
        logger.info(f"Added notification channel: {channel.channel_id}")
    
    def add_custom_handler(self, channel_id: str, handler: Callable):
        """Добавление пользовательского обработчика уведомлений"""
        self.custom_handlers[channel_id] = handler
        logger.info(f"Added custom handler for channel: {channel_id}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Подтверждение алерта"""
        if not self.clickhouse_client:
            return False
        
        try:
            # Обновление статуса алерта
            query = """
            ALTER TABLE rag.alerts UPDATE 
            status = 'acknowledged',
            acknowledged_at = now(),
            acknowledged_by = %(acknowledged_by)s
            WHERE alert_id = %(alert_id)s
            """
            
            self.clickhouse_client.command(
                query,
                parameters={'alert_id': alert_id, 'acknowledged_by': acknowledged_by}
            )
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str):
        """Разрешение алерта"""
        if not self.clickhouse_client:
            return False
        
        try:
            query = """
            ALTER TABLE rag.alerts UPDATE 
            status = 'resolved',
            resolved_at = now()
            WHERE alert_id = %(alert_id)s
            """
            
            self.clickhouse_client.command(
                query,
                parameters={'alert_id': alert_id}
            )
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return False
    
    async def get_active_alerts(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение активных алертов"""
        if not self.clickhouse_client:
            return []
        
        try:
            where_clause = "WHERE status = 'active'"
            params = {}
            
            if service:
                where_clause += " AND service = %(service)s"
                params['service'] = service
            
            query = f"""
            SELECT 
                alert_id,
                alert_type,
                severity,
                service,
                message,
                timestamp,
                metadata
            FROM rag.alerts
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT 100
            """
            
            result = self.clickhouse_client.query(query, parameters=params)
            
            alerts = []
            for row in result.result_rows:
                alerts.append({
                    'alert_id': row[0],
                    'alert_type': row[1],
                    'severity': row[2],
                    'service': row[3],
                    'message': row[4],
                    'timestamp': row[5],
                    'metadata': row[6]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def start_monitoring(self):
        """Запуск мониторинга алертов"""
        logger.info("Starting alert monitoring")
        
        while True:
            try:
                await self.check_alert_rules()
                await asyncio.sleep(60)  # Проверка каждую минуту
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(60)


# Глобальный экземпляр системы алертов
alert_system = AlertSystem()


def get_alert_system() -> AlertSystem:
    """Получение экземпляра системы алертов"""
    return alert_system
