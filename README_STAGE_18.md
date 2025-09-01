# Этап 18: CI/CD и развертывание

## 🚀 Обзор

Этап 18 создает полную систему автоматизации CI/CD для RAG платформы, включающую GitHub Actions, автоматическую сборку Docker образов, развертывание в Kubernetes через Helm, и GitLab CI зеркало для резервирования.

## ✅ Реализованная CI/CD система

### 1. 🔄 GitHub Actions CI/CD

#### Структура workflows
```
.github/workflows/
├── ci.yml                   # Continuous Integration pipeline
└── build-and-deploy.yml     # Build and Deployment pipeline
```

#### CI Pipeline (ci.yml)
```yaml
jobs:
  code-quality:     # 🔍 Code Quality & Security
  unit-tests:       # 🔬 Unit Tests (Python 3.11, 3.12)
  integration-tests: # 🔗 Integration Tests (PostgreSQL, Redis, ClickHouse)
  e2e-tests:        # 🎭 End-to-End Tests (Playwright)
  performance-tests: # ⚡ Performance Tests (Load testing)
  build-summary:    # 📋 Build Status Summary
```

#### Возможности CI Pipeline
- **Code Quality**: Black, isort, flake8, mypy, bandit, safety
- **Multi-version testing**: Python 3.11 и 3.12
- **Real services**: PostgreSQL с pgvector, Redis, ClickHouse
- **Coverage reporting**: Codecov integration с 80%+ требованием
- **Security scanning**: Bandit, Safety, dependency checks
- **Performance validation**: Load tests с метриками RPS и latency

#### Build & Deploy Pipeline (build-and-deploy.yml)
```yaml
jobs:
  build-images:     # 🐳 Multi-platform Docker builds
  security-scan:    # 🛡️ Container security scanning
  deploy-staging:   # 🎭 Staging deployment
  smoke-tests:      # 💨 Smoke tests validation
  deploy-production: # 🚀 Blue-Green production deployment
  notify:           # 📢 Team notifications
```

#### Возможности Build & Deploy
- **Multi-platform builds**: linux/amd64, linux/arm64
- **Container registry**: GitHub Container Registry (GHCR)
- **Security scanning**: Trivy, Snyk vulnerability scans
- **SBOM generation**: Software Bill of Materials
- **Blue-Green deployment**: Zero-downtime production deployments
- **Auto-scaling**: HPA для production с 3-10 replicas
- **Monitoring integration**: Prometheus, Grafana, AlertManager

### 2. 🐳 Docker Images Build System

#### Автоматическая сборка для компонентов
```bash
# Компоненты для сборки
- API Service (FastAPI)
- Streamlit Frontend  
- Superset Dashboards
- Airflow Pipelines

# Build стратегия
- Multi-platform: amd64 + arm64
- Cache optimization: GitHub Actions cache
- Security scanning: Trivy + Snyk
- SBOM generation: Anchore
- Image signing: Cosign (опционально)
```

#### Docker Build Features
```yaml
# Build arguments
BUILD_DATE: ${{ fromJSON(steps.meta.outputs.json).labels['org.opencontainers.image.created'] }}
VCS_REF: ${{ github.sha }}
VERSION: ${{ fromJSON(steps.meta.outputs.json).labels['org.opencontainers.image.version'] }}

# Cache strategy
cache-from: type=gha
cache-to: type=gha,mode=max

# Multi-platform
platforms: linux/amd64,linux/arm64
```

### 3. 📦 GitHub Container Registry Integration

#### Image Tagging Strategy
```yaml
tags: |
  type=ref,event=branch          # main, develop
  type=ref,event=pr              # pr-123
  type=semver,pattern={{version}} # v1.2.3
  type=semver,pattern={{major}}.{{minor}} # v1.2
  type=sha,prefix={{branch}}-     # main-abc1234
  type=raw,value=latest,enable={{is_default_branch}} # latest
```

#### Registry Features
- **Automatic tagging**: Based on git refs, semver, SHA
- **Multi-component**: Separate images per service
- **Retention policy**: Automatic cleanup старых образов
- **Access control**: GitHub Teams integration
- **Vulnerability scanning**: Integrated security reports

### 4. 🚀 Kubernetes Helm Deployment

#### Helm Chart Structure
```
infra/helm/rag-platform/
├── Chart.yaml              # Chart metadata and dependencies
├── values.yaml             # Default configuration values
├── templates/
│   ├── _helpers.tpl         # Template helpers
│   ├── api-deployment.yaml  # API service deployment
│   ├── streamlit-deployment.yaml
│   ├── superset-deployment.yaml
│   ├── configmaps.yaml      # Configuration management
│   ├── secrets.yaml         # Secret management
│   ├── services.yaml        # Kubernetes services
│   ├── ingress.yaml         # Ingress configuration
│   └── hpa.yaml            # Horizontal Pod Autoscaler
└── values/
    ├── staging.yaml         # Staging environment values
    └── production.yaml      # Production environment values
```

#### Chart Dependencies
```yaml
dependencies:
  - postgresql: ^12.0.0      # Primary database with pgvector
  - redis: ^18.0.0           # Caching and message broker
  - clickhouse: ^3.0.0       # Analytics database
  - prometheus: ^23.0.0      # Monitoring and metrics
  - grafana: ^7.0.0          # Visualization dashboards
```

#### Deployment Strategies
```yaml
# Staging Environment
api:
  replicas: 2
  resources:
    requests: { cpu: 200m, memory: 512Mi }
    limits: { cpu: 1000m, memory: 1Gi }

# Production Environment  
api:
  replicas: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
  resources:
    requests: { cpu: 500m, memory: 1Gi }
    limits: { cpu: 2000m, memory: 4Gi }
```

#### Blue-Green Deployment
```bash
# Production deployment process
1. Deploy GREEN version alongside BLUE
2. Health check GREEN deployment
3. Switch traffic from BLUE to GREEN
4. Grace period (5 minutes)
5. Remove BLUE deployment
6. Rename GREEN to BLUE for next cycle
```

### 5. 🔄 GitLab CI Mirror

#### GitLab Pipeline Structure
```yaml
stages:
  - validate    # 🔍 Code quality and Docker validation
  - test        # 🧪 Unit, integration, E2E tests
  - security    # 🛡️ Security and SAST scanning
  - build       # 🐳 Docker images build
  - deploy      # 🚀 Staging and production deployment
  - notify      # 📢 Team notifications
```

#### GitLab Features
- **Mirror functionality**: Полное дублирование GitHub Actions
- **GitLab Registry**: Альтернативный container registry
- **SAST integration**: Built-in security scanning
- **Performance testing**: Scheduled load tests
- **Multi-environment**: Staging и production deployments
- **Cleanup automation**: Registry и resource cleanup

#### Security Integration
```yaml
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml  
  - template: Security/License-Scanning.gitlab-ci.yml
```

### 6. 📋 Local Development Deployment

#### deploy_local.sh Script Features
```bash
# Deployment methods
./deploy_local.sh -m docker      # Docker Compose (default)
./deploy_local.sh -m kubernetes  # Direct Kubernetes
./deploy_local.sh -m helm        # Helm chart

# Configuration options
-e, --env ENV         # Environment: local|dev|test
-c, --clean           # Clean existing deployment  
-b, --build           # Force rebuild images
-p, --pull            # Update base images
-s, --skip-tests      # Skip health checks
-v, --verbose         # Verbose output
--no-cache            # Build without cache
```

#### Local Deployment Capabilities
- **Multi-method support**: Docker Compose, Kubernetes, Helm
- **Environment management**: local, dev, test configurations
- **Health checking**: Automatic service validation
- **Resource monitoring**: Container stats and Kubernetes metrics
- **Port management**: Automatic port conflict resolution
- **Cleanup automation**: Complete environment teardown

#### Docker Compose Configuration
```yaml
# Generated .env.local
STREAMLIT_PORT=8502
API_PORT=8081
SUPERSET_PORT=8090
POSTGRES_PORT=5433
REDIS_PORT=6380
CLICKHOUSE_PORT=8124

# Service URLs
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rag_db
REDIS_URL=redis://redis:6379/0
CLICKHOUSE_URL=http://clickhouse:8123
```

## 🛠️ Infrastructure as Code

### Environment Management
```yaml
# Staging Environment
global:
  environment: staging
  domain: staging.rag-platform.com
  
resources:
  api: { requests: { cpu: 200m, memory: 512Mi } }
  streamlit: { requests: { cpu: 100m, memory: 256Mi } }

database:
  postgresql: { persistence: { size: 100Gi } }
  redis: { persistence: { size: 20Gi } }

# Production Environment
global:
  environment: production
  domain: rag-platform.com

resources:
  api: { requests: { cpu: 500m, memory: 1Gi } }
  streamlit: { requests: { cpu: 200m, memory: 512Mi } }

database:
  postgresql: 
    primary: { persistence: { size: 500Gi } }
    readReplicas: { replicaCount: 2 }
  redis: 
    cluster: { enabled: true, nodes: 6 }
```

### Security Configuration
```yaml
security:
  podSecurityPolicy: { enabled: false }
  networkPolicy: { enabled: false }
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000

secrets:
  generate: { enabled: true, length: 32 }
  external: { enabled: false, secretManager: "aws" }
```

### Monitoring & Observability
```yaml
monitoring:
  prometheus:
    enabled: true
    server: { persistentVolume: { size: 50Gi } }
    alertmanager: { persistentVolume: { size: 10Gi } }
  
  grafana:
    enabled: true
    persistence: { size: 10Gi }
    admin: { existingSecret: "grafana-admin" }
```

## 📊 Deployment Workflows

### 1. Feature Development Flow
```mermaid
graph TD
    A[Developer Push] --> B[GitHub Actions CI]
    B --> C[Code Quality Checks]
    C --> D[Unit Tests]
    D --> E[Integration Tests]
    E --> F[Security Scan]
    F --> G[Build Images]
    G --> H[Deploy to Dev]
    H --> I[Smoke Tests]
```

### 2. Release Flow
```mermaid
graph TD
    A[Git Tag v1.2.3] --> B[GitHub Actions Build]
    B --> C[Multi-platform Build]
    C --> D[Security Scan]
    D --> E[Deploy to Staging]
    E --> F[E2E Tests]
    F --> G[Manual Approval]
    G --> H[Blue-Green Production Deploy]
    H --> I[Health Check]
    I --> J[Traffic Switch]
    J --> K[Cleanup Old Version]
```

### 3. GitLab Mirror Flow
```mermaid
graph TD
    A[GitLab Push] --> B[GitLab CI Pipeline]
    B --> C[Parallel GitHub Sync]
    C --> D[SAST Scanning]
    D --> E[Build & Test]
    E --> F[Registry Push]
    F --> G[Deploy to GitLab Env]
```

## 🔧 Configuration Management

### Secrets Management
```bash
# GitHub Secrets (required)
GITHUB_TOKEN              # Container registry access
AWS_ACCESS_KEY_ID          # EKS cluster access
AWS_SECRET_ACCESS_KEY      # EKS cluster access
SLACK_WEBHOOK             # Team notifications
EMAIL_USERNAME            # Email notifications
EMAIL_PASSWORD            # Email notifications
NOTIFICATION_EMAIL        # Failure notifications
SNYK_TOKEN               # Security scanning (optional)

# GitLab Variables (required)
KUBE_CONFIG              # Kubernetes config (base64)
KUBE_CONFIG_PROD         # Production config (base64)
SLACK_WEBHOOK_URL        # Team notifications
CI_REGISTRY_PASSWORD     # Container registry access
```

### Environment Variables
```yaml
# API Service
DATABASE_URL: "postgresql://postgres:postgres@rag-platform-postgresql:5432/rag_db"
REDIS_URL: "redis://rag-platform-redis-master:6379/0"
CLICKHOUSE_URL: "http://rag-platform-clickhouse:8123"
OLLAMA_BASE_URL: "http://ollama:11434"
JWT_SECRET_KEY: "${GENERATED_SECRET}"
ENVIRONMENT: "production"
LOG_LEVEL: "INFO"
CORS_ORIGINS: "*"

# Streamlit Frontend
API_BASE_URL: "http://rag-platform-api:8081"
STREAMLIT_SERVER_PORT: "8502"
STREAMLIT_BROWSER_GATHER_USAGE_STATS: "false"
```

### Ingress Configuration
```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
  
  hosts:
    - host: rag-platform.com
      paths:
        - path: /           # Streamlit Frontend
        - path: /api        # FastAPI Backend
        - path: /superset   # Superset Dashboards
        - path: /airflow    # Airflow UI
  
  tls:
    - secretName: rag-platform-tls
      hosts: [rag-platform.com]
```

## 📈 Performance & Scaling

### Auto-scaling Configuration
```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

streamlit:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 8
    targetCPUUtilizationPercentage: 70
```

### Resource Allocation
```yaml
# Production Resources
api:
  resources:
    requests: { cpu: 500m, memory: 1Gi }
    limits: { cpu: 2000m, memory: 4Gi }

streamlit:
  resources:
    requests: { cpu: 200m, memory: 512Mi }
    limits: { cpu: 1000m, memory: 1Gi }

postgresql:
  primary:
    resources:
      requests: { cpu: 1000m, memory: 2Gi }
      limits: { cpu: 4000m, memory: 8Gi }
```

### Database Scaling
```yaml
postgresql:
  primary:
    persistence: { size: 500Gi, storageClass: gp3 }
  readReplicas:
    replicaCount: 2
    persistence: { size: 500Gi }

redis:
  cluster:
    enabled: true
    nodes: 6
    
clickhouse:
  shards: 3
  replicas: 2
  persistence: { size: 1Ti, storageClass: gp3 }
```

## 🛡️ Security & Compliance

### Container Security
```yaml
# Security scanning in CI/CD
- Trivy vulnerability scanning
- Snyk dependency analysis  
- SAST code analysis
- Secret detection
- License compliance
- SBOM generation
```

### Runtime Security
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true

networkPolicy:
  enabled: true
  ingress:
    - from: [namespaceSelector: {matchLabels: {name: ingress-nginx}}]
  egress:
    - to: [namespaceSelector: {matchLabels: {name: kube-system}}]
```

### Secrets Management
```yaml
# Automatic secret generation
JWT_SECRET_KEY: $(openssl rand -hex 32)
POSTGRES_PASSWORD: $(openssl rand -base64 32)
SUPERSET_SECRET_KEY: $(openssl rand -hex 32)
AIRFLOW_FERNET_KEY: $(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# External secrets (optional)
external:
  enabled: false
  secretManager: "aws"  # aws, azure, gcp, vault
```

## 📊 Monitoring & Alerting

### Deployment Monitoring
```yaml
# Health checks
livenessProbe:
  httpGet: { path: /health, port: 8081 }
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet: { path: /ready, port: 8081 }
  initialDelaySeconds: 15
  periodSeconds: 5
```

### Metrics Collection
```yaml
prometheus:
  enabled: true
  server:
    persistentVolume: { size: 50Gi }
  alertmanager:
    enabled: true
    persistentVolume: { size: 10Gi }

grafana:
  enabled: true
  persistence: { size: 10Gi }
  dashboards:
    - RAG Platform Overview
    - API Performance
    - Database Metrics
    - Container Resources
```

### Notification Integration
```yaml
# Slack notifications
- Deployment success/failure
- Security scan results
- Performance test results
- Health check failures

# Email notifications  
- Critical deployment failures
- Security vulnerabilities
- Resource limit exceeded
```

## 🎯 Best Practices

### 1. GitOps Workflow
- **Infrastructure as Code**: Все в Git репозитории
- **Declarative deployments**: Kubernetes манифесты
- **Immutable deployments**: Container images с неизменяемыми тегами
- **Rollback capability**: Быстрый откат к предыдущей версии

### 2. Security First
- **Least privilege**: Минимальные права доступа
- **Network policies**: Ограничение сетевого трафика
- **Secret rotation**: Автоматическая смена секретов
- **Vulnerability scanning**: На каждом этапе pipeline

### 3. Zero Downtime Deployments
- **Blue-Green strategy**: Переключение без остановки
- **Health checks**: Проверка готовности перед переключением
- **Database migrations**: Безопасные схемы обновлений
- **Traffic management**: Постепенное переключение нагрузки

### 4. Observability
- **Structured logging**: JSON формат с correlation ID
- **Metrics collection**: Prometheus + Grafana
- **Distributed tracing**: Jaeger/Zipkin интеграция
- **Error tracking**: Sentry для production ошибок

## 🚀 Deployment Commands

### GitHub Actions
```bash
# Trigger workflows
git tag v1.2.3                    # Production deployment
git push origin main               # Staging deployment
gh workflow run build-and-deploy  # Manual trigger

# Monitor workflows
gh run list --workflow=ci.yml
gh run view --log
```

### Local Development
```bash
# Docker Compose deployment
./scripts/deploy_local.sh

# Kubernetes deployment  
./scripts/deploy_local.sh -m kubernetes

# Helm deployment
./scripts/deploy_local.sh -m helm -e dev

# Cleanup and rebuild
./scripts/deploy_local.sh -c -b --no-cache
```

### Production Management
```bash
# Helm operations
helm status rag-platform-production -n rag-platform-production
helm rollback rag-platform-production 1 -n rag-platform-production
helm upgrade rag-platform-production ./infra/helm/rag-platform -n rag-platform-production

# Kubernetes operations
kubectl get all -n rag-platform-production
kubectl logs -f deployment/rag-platform-api -n rag-platform-production
kubectl port-forward svc/rag-platform-api 8081:8081 -n rag-platform-production
```

## 🏆 Заключение этапа

Этап 18 создает enterprise-grade CI/CD систему:

✅ **GitHub Actions CI/CD** с 6-job pipeline и multi-environment deployment  
✅ **Multi-platform Docker builds** для amd64/arm64 с security scanning  
✅ **GHCR integration** с automatic tagging и retention policies  
✅ **Kubernetes Helm deployment** с blue-green production strategy  
✅ **GitLab CI mirror** для полного резервирования pipeline  
✅ **Local development tools** с multi-method deployment support  
✅ **Security-first approach** с vulnerability scanning и SAST  
✅ **Zero-downtime deployments** с health checks и traffic switching  
✅ **Auto-scaling configuration** для production workloads  
✅ **Complete observability** с Prometheus, Grafana, и alerting  

**Production-ready CI/CD система готова для enterprise использования!** 🚀

Переходим к **Этапу 19: Документация и обучение** 📚
