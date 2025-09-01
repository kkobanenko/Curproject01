# 🛠️ RAG Platform Support Runbook
## Операционное руководство для технической поддержки

### 📋 Оглавление

1. [🚨 Процедуры экстренного реагирования](#-процедуры-экстренного-реагирования)
2. [🔍 Диагностика и troubleshooting](#-диагностика-и-troubleshooting)
3. [📊 Мониторинг и алерты](#-мониторинг-и-алерты)
4. [🔧 Стандартные процедуры](#-стандартные-процедуры)
5. [📞 Эскалация инцидентов](#-эскалация-инцидентов)
6. [📝 Документирование и отчетность](#-документирование-и-отчетность)

## 🚨 Процедуры экстренного реагирования

### P1 - Критические инциденты (Full Outage)

#### 🚩 Признаки
- Недоступность API (HTTP 5xx, timeouts)
- Недоступность веб-интерфейса
- Падение базы данных
- Критические ошибки безопасности

#### ⚡ Немедленные действия (первые 15 минут)

```bash
# 1. Проверка статуса всех сервисов
./scripts/health_check.sh

# 2. Проверка Docker контейнеров
docker ps -a
docker logs rag-platform-api-prod
docker logs rag-platform-streamlit-prod
docker logs rag-platform-postgres-prod

# 3. Проверка системных ресурсов
htop
df -h
free -h
iostat -x 1 5

# 4. Проверка сетевых подключений
netstat -tulpn | grep -E "(8081|8502|5432|6379|8123)"
```

#### 🔧 Базовые действия восстановления

```bash
# Перезапуск всех сервисов
cd /opt/rag-platform
docker-compose -f infra/production/docker-compose.prod.yml restart

# Если не помогает - полная перезагрузка
docker-compose -f infra/production/docker-compose.prod.yml down
docker-compose -f infra/production/docker-compose.prod.yml up -d

# Проверка логов после перезапуска
./scripts/health_check.sh
```

#### 📞 Уведомления
1. **Немедленно** уведомить команду в Slack/Teams
2. **Через 15 минут** эскалировать к Senior Engineer
3. **Через 30 минут** уведомить клиентов через status page
4. **Через 1 час** эскалировать к Technical Director

### P2 - Серьезные инциденты (Performance Degradation)

#### 🚩 Признаки  
- Медленные ответы API (>2 секунд)
- Высокое использование ресурсов (>90%)
- Частые ошибки 503/504
- Проблемы с обработкой документов

#### 🔍 Диагностические команды

```bash
# Проверка производительности API
curl -w "Total time: %{time_total}s\n" http://localhost:8081/health

# Мониторинг ресурсов
top -p $(pgrep -f rag-platform)
docker stats

# Проверка базы данных
docker exec rag-platform-postgres-prod psql -U postgres -d rag_platform -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# Проверка Redis
docker exec rag-platform-redis-prod redis-cli info memory
docker exec rag-platform-redis-prod redis-cli slowlog get 10
```

## 🔍 Диагностика и troubleshooting

### 📊 Системный мониторинг

#### Основные команды для диагностики

```bash
# Общее состояние системы
./scripts/system_status.sh

# Проверка дискового пространства
df -h
du -sh /var/lib/docker
du -sh /opt/rag-platform

# Анализ логов
journalctl -u docker -f
tail -f /var/log/nginx/error.log
docker logs --tail=100 -f rag-platform-api-prod

# Сетевая диагностика
ss -tulpn
iptables -L
ping 8.8.8.8
```

#### Специфичные проверки RAG Platform

```bash
# API Health Check
curl -I http://localhost:8081/health
curl -X POST http://localhost:8081/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 1}'

# Database connectivity
docker exec rag-platform-postgres-prod pg_isready -U postgres

# Redis connectivity  
docker exec rag-platform-redis-prod redis-cli ping

# ClickHouse connectivity
docker exec rag-platform-clickhouse-prod clickhouse-client --query "SELECT 1"

# Ollama status
curl http://localhost:11434/api/tags
```

### 🔧 Типичные проблемы и решения

#### Problem: API возвращает 500 ошибки

**Диагностика:**
```bash
# Проверка логов API
docker logs rag-platform-api-prod | tail -50

# Проверка подключения к базе
docker exec rag-platform-api-prod python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
print('DB Connection:', engine.execute('SELECT 1').scalar())
"
```

**Решение:**
```bash
# Перезапуск API сервиса
docker restart rag-platform-api-prod

# Если проблема в базе - перезапуск PostgreSQL
docker restart rag-platform-postgres-prod
```

#### Problem: Медленные поиски

**Диагностика:**
```bash
# Проверка индексов в PostgreSQL
docker exec rag-platform-postgres-prod psql -U postgres -d rag_platform -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename LIKE '%document%' OR tablename LIKE '%embedding%';"

# Проверка запросов
docker exec rag-platform-postgres-prod psql -U postgres -d rag_platform -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;"
```

**Решение:**
```bash
# Переиндексация
docker exec rag-platform-postgres-prod psql -U postgres -d rag_platform -c "
REINDEX INDEX CONCURRENTLY idx_embeddings_vector;"

# Очистка кеша
docker exec rag-platform-redis-prod redis-cli FLUSHDB
```

#### Problem: Высокое использование памяти

**Диагностика:**
```bash
# Анализ использования памяти по контейнерам
docker stats --no-stream

# Детальный анализ процессов
ps aux --sort=-%mem | head -20

# Проверка PostgreSQL
docker exec rag-platform-postgres-prod psql -U postgres -c "
SELECT setting, unit FROM pg_settings WHERE name IN (
    'shared_buffers', 'work_mem', 'maintenance_work_mem'
);"
```

**Решение:**
```bash
# Оптимизация PostgreSQL
docker exec rag-platform-postgres-prod psql -U postgres -c "
SET work_mem = '4MB';
SET maintenance_work_mem = '64MB';"

# Перезапуск с ограничением памяти
docker update --memory="2g" rag-platform-postgres-prod
```

## 📊 Мониторинг и алерты

### 🔔 Настройка алертов

#### Критические алерты (немедленная реакция)

```yaml
# Prometheus alerts
groups:
  - name: critical
    rules:
    - alert: ServiceDown
      expr: up == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        description: "Service {{ $labels.job }} is down"
        
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
      for: 5m
      labels:
        severity: critical
```

#### Мониторинг в Grafana

**Основные дашборды:**
- System Overview: CPU, Memory, Disk, Network
- Application Metrics: API response times, error rates
- Database Performance: Query times, connections
- User Activity: Active users, request patterns

### 📈 Ключевые метрики для отслеживания

| Метрика | Норма | Предупреждение | Критично |
|---------|-------|----------------|----------|
| API Response Time | <500ms | >1s | >2s |
| Error Rate | <1% | >5% | >10% |
| CPU Usage | <70% | >80% | >90% |
| Memory Usage | <80% | >90% | >95% |
| Disk Usage | <80% | >90% | >95% |
| DB Connections | <80% max | >90% max | >95% max |

## 🔧 Стандартные процедуры

### 🔄 Ежедневные проверки

```bash
#!/bin/bash
# Daily health check script

echo "=== Daily RAG Platform Health Check ==="
date

echo "1. Service Status:"
./scripts/health_check.sh

echo "2. Resource Usage:"
df -h | grep -E "(/$|/var|/opt)"
free -h
docker system df

echo "3. Application Metrics:"
curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result[] | {job: .metric.job, status: .value[1]}'

echo "4. Error Logs (last hour):"
docker logs --since="1h" rag-platform-api-prod 2>&1 | grep -i error | tail -10

echo "5. Performance Check:"
curl -w "API Response Time: %{time_total}s\n" -o /dev/null -s http://localhost:8081/health
```

### 📅 Еженедельные задачи

```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly RAG Platform Maintenance ==="

echo "1. Database Maintenance:"
docker exec rag-platform-postgres-prod psql -U postgres -d rag_platform -c "VACUUM ANALYZE;"

echo "2. Log Rotation:"
docker logs rag-platform-api-prod > /var/log/rag-platform/api-$(date +%Y%m%d).log
docker exec rag-platform-api-prod truncate -s 0 /var/log/*.log

echo "3. Cleanup Old Data:"
docker exec rag-platform-redis-prod redis-cli --eval "
for i=0,redis.call('dbsize')-1 do
    local key = redis.call('randomkey')
    if key and redis.call('ttl',key) == -1 then
        redis.call('expire',key,86400*7)
    end
end" 0

echo "4. Security Update Check:"
docker images | grep -v REPOSITORY | awk '{print $1":"$2}' | xargs -I {} docker pull {}

echo "5. Backup Verification:"
./scripts/backup_system.sh --verify-last
```

### 🗓️ Ежемесячные процедуры

1. **Performance Review**
   - Анализ трендов производительности
   - Планирование capacity
   - Оптимизация конфигураций

2. **Security Audit**
   - Проверка access logs
   - Анализ security events
   - Обновление security политик

3. **Disaster Recovery Test**
   - Тестирование backup/restore
   - Проверка failover процедур
   - Документирование RTO/RPO

## 📞 Эскалация инцидентов

### 🔄 Матрица эскалации

| Уровень | Роль | Контакт | Эскалация |
|---------|------|---------|-----------|
| **L1** | Support Engineer | support@company.com | 30 мин |
| **L2** | Senior Engineer | senior@company.com | 1 час |
| **L3** | DevOps Lead | devops@company.com | 2 часа |
| **L4** | Technical Director | tech-director@company.com | 4 часа |

### 📋 Процесс эскалации

1. **Создание ticket** в системе управления инцидентами
2. **Уведомление команды** через Slack/Teams
3. **Регулярные обновления** каждые 30 минут
4. **Автоматическая эскалация** при превышении SLA
5. **Post-mortem анализ** для критических инцидентов

### 🚨 Emergency Contacts

**24/7 Emergency Hotline**: +7 (495) 123-45-67  
**Emergency Email**: emergency@rag-platform.com  
**Status Page**: https://status.rag-platform.com  

## 📝 Документирование и отчетность

### 📊 Incident Report Template

```markdown
# Incident Report #YYYY-MM-DD-001

## Summary
- **Date/Time**: 
- **Duration**: 
- **Severity**: P1/P2/P3/P4
- **Affected Services**: 
- **Impact**: 

## Timeline
- **XX:XX** - Incident detected
- **XX:XX** - Investigation started
- **XX:XX** - Root cause identified
- **XX:XX** - Fix applied
- **XX:XX** - Service restored
- **XX:XX** - Incident closed

## Root Cause
[Detailed analysis of what caused the incident]

## Resolution
[Description of how the incident was resolved]

## Prevention Measures
[Actions taken to prevent similar incidents]

## Lessons Learned
[Key takeaways and improvements]
```

### 📈 Monthly Report Template

1. **Availability Summary**
   - Uptime statistics
   - SLA compliance
   - Major incidents

2. **Performance Metrics**
   - Response times
   - Throughput
   - Resource utilization

3. **Incident Analysis**
   - Total incidents by category
   - MTTR trends
   - Top issues

4. **Improvements Implemented**
   - System optimizations
   - Process improvements
   - Documentation updates

5. **Action Items**
   - Outstanding issues
   - Planned improvements
   - Resource requirements

### 🔍 Knowledge Base Maintenance

- **Weekly**: Update troubleshooting guides
- **Monthly**: Review and update procedures
- **Quarterly**: Comprehensive knowledge base audit
- **Annually**: Full documentation review

---

**Контакт для обновлений runbook**: support-docs@rag-platform.com  
**Последнее обновление**: 19 декабря 2024  
**Версия**: 1.0
