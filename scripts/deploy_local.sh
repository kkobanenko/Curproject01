#!/bin/bash

# Локальный деплой RAG Platform для разработки и тестирования

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции вывода
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Конфигурация
ENVIRONMENT="local"
NAMESPACE="rag-platform-local"
COMPOSE_FILE="infra/compose/docker-compose.yml"
HELM_CHART="infra/helm/rag-platform"
DEPLOY_METHOD="docker"  # docker | kubernetes | helm

# Функция помощи
show_help() {
    cat << EOF
Скрипт локального развертывания RAG Platform

ИСПОЛЬЗОВАНИЕ:
    ./deploy_local.sh [ОПЦИИ]

ОПЦИИ:
    -m, --method METHOD    Метод развертывания: docker|kubernetes|helm (по умолчанию: docker)
    -e, --env ENV         Окружение: local|dev|test (по умолчанию: local)
    -c, --clean           Очистить существующее развертывание
    -b, --build           Принудительная пересборка образов
    -p, --pull            Обновить base образы
    -s, --skip-tests      Пропустить проверочные тесты
    -v, --verbose         Подробный вывод
    --no-cache            Сборка без кэша
    --help                Показать эту справку

ПРИМЕРЫ:
    ./deploy_local.sh                           # Docker Compose развертывание
    ./deploy_local.sh -m kubernetes             # Kubernetes развертывание
    ./deploy_local.sh -m helm -e dev            # Helm развертывание для dev
    ./deploy_local.sh -c -b                     # Очистка и пересборка
    ./deploy_local.sh --no-cache -v             # Полная пересборка с логами

МЕТОДЫ РАЗВЕРТЫВАНИЯ:
    docker      - Docker Compose (рекомендуется для разработки)
    kubernetes  - Прямое развертывание в Kubernetes
    helm        - Развертывание через Helm chart
EOF
}

# Парсинг аргументов
CLEAN=false
BUILD=false
PULL=false
SKIP_TESTS=false
VERBOSE=false
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--method)
            DEPLOY_METHOD="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -p|--pull)
            PULL=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
done

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker не найден. Установите Docker Desktop или Docker Engine."
        exit 1
    fi
    
    # Docker Compose
    if [[ "$DEPLOY_METHOD" == "docker" ]]; then
        if ! docker compose version &> /dev/null; then
            error "Docker Compose не найден."
            exit 1
        fi
    fi
    
    # Kubernetes
    if [[ "$DEPLOY_METHOD" == "kubernetes" || "$DEPLOY_METHOD" == "helm" ]]; then
        if ! command -v kubectl &> /dev/null; then
            error "kubectl не найден. Установите kubectl."
            exit 1
        fi
        
        # Проверка подключения к кластеру
        if ! kubectl cluster-info &> /dev/null; then
            error "Нет подключения к Kubernetes кластеру."
            warning "Запустите minikube, kind или подключитесь к удаленному кластеру."
            exit 1
        fi
    fi
    
    # Helm
    if [[ "$DEPLOY_METHOD" == "helm" ]]; then
        if ! command -v helm &> /dev/null; then
            error "Helm не найден. Установите Helm."
            exit 1
        fi
    fi
    
    success "Зависимости проверены"
}

# Очистка существующего развертывания
cleanup_deployment() {
    if [[ "$CLEAN" == true ]]; then
        log "Очистка существующего развертывания..."
        
        case $DEPLOY_METHOD in
            docker)
                cd infra/compose
                docker compose -f docker-compose.yml down -v --remove-orphans || true
                docker system prune -f || true
                ;;
            kubernetes)
                kubectl delete namespace $NAMESPACE --ignore-not-found=true
                ;;
            helm)
                helm uninstall rag-platform-$ENVIRONMENT -n $NAMESPACE || true
                kubectl delete namespace $NAMESPACE --ignore-not-found=true
                ;;
        esac
        
        success "Очистка завершена"
    fi
}

# Подготовка образов
prepare_images() {
    log "Подготовка Docker образов..."
    
    # Обновление base образов
    if [[ "$PULL" == true ]]; then
        log "Обновление base образов..."
        docker pull python:3.11-slim
        docker pull node:18-alpine
        docker pull nginx:alpine
        docker pull postgres:15
        docker pull redis:7-alpine
        docker pull clickhouse/clickhouse-server:23.3
        docker pull ollama/ollama:latest
    fi
    
    # Сборка локальных образов
    if [[ "$BUILD" == true ]]; then
        log "Сборка локальных образов..."
        
        BUILD_ARGS=""
        if [[ "$NO_CACHE" == true ]]; then
            BUILD_ARGS="--no-cache"
        fi
        
        if [[ "$VERBOSE" == true ]]; then
            BUILD_ARGS="$BUILD_ARGS --progress=plain"
        fi
        
        # API
        log "Сборка API образа..."
        docker build $BUILD_ARGS -t rag-platform/api:local \
            -f apps/api/Dockerfile apps/api/
        
        # Streamlit
        log "Сборка Streamlit образа..."
        docker build $BUILD_ARGS -t rag-platform/streamlit:local \
            -f apps/streamlit_app/Dockerfile apps/streamlit_app/
        
        # Superset (если нужен)
        if [[ -f "infra/superset/Dockerfile" ]]; then
            log "Сборка Superset образа..."
            docker build $BUILD_ARGS -t rag-platform/superset:local \
                -f infra/superset/Dockerfile infra/superset/
        fi
        
        # Airflow (если нужен)
        if [[ -f "pipelines/airflow/Dockerfile" ]]; then
            log "Сборка Airflow образа..."
            docker build $BUILD_ARGS -t rag-platform/airflow:local \
                -f pipelines/airflow/Dockerfile pipelines/airflow/
        fi
        
        success "Образы собраны"
    fi
}

# Подготовка конфигурации
prepare_config() {
    log "Подготовка конфигурации для $ENVIRONMENT..."
    
    case $DEPLOY_METHOD in
        docker)
            # Создаем локальный .env файл
            cat > infra/compose/.env.local << EOF
# Локальная конфигурация RAG Platform
ENVIRONMENT=$ENVIRONMENT

# Порты сервисов
STREAMLIT_PORT=8502
API_PORT=8081
SUPERSET_PORT=8090
AIRFLOW_PORT=8080
POSTGRES_PORT=5433
REDIS_PORT=6380
CLICKHOUSE_PORT=8124
OLLAMA_PORT=11434

# URL подключений
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rag_db
REDIS_URL=redis://redis:6379/0
CLICKHOUSE_URL=http://clickhouse:8123
OLLAMA_BASE_URL=http://ollama:11434

# Настройки безопасности
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Настройки кэша
CACHE_TTL=3600
REDIS_TTL=7200

# Настройки логирования
LOG_LEVEL=INFO

# Настройки развертывания
COMPOSE_PROJECT_NAME=rag-platform-$ENVIRONMENT
EOF
            ;;
        kubernetes)
            # Создаем namespace
            kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
            
            # Создаем secrets
            kubectl create secret generic rag-platform-secrets \
                --namespace=$NAMESPACE \
                --from-literal=jwt-secret-key=$(openssl rand -hex 32) \
                --from-literal=postgres-password=postgres \
                --from-literal=superset-secret-key=$(openssl rand -hex 32) \
                --from-literal=airflow-fernet-key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
                --dry-run=client -o yaml | kubectl apply -f -
            ;;
        helm)
            # Создаем namespace
            kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
            
            # Подготавливаем values файл
            cat > /tmp/local-values.yaml << EOF
global:
  environment: $ENVIRONMENT
  imageTag: local
  domain: localhost
  imagePullPolicy: Never

api:
  image: rag-platform/api
  tag: local
  replicas: 1
  service:
    type: NodePort

streamlit:
  image: rag-platform/streamlit
  tag: local
  replicas: 1
  service:
    type: NodePort

superset:
  enabled: false

airflow:
  enabled: false

postgresql:
  enabled: true
  auth:
    postgresPassword: postgres

redis:
  enabled: true
  auth:
    enabled: false

clickhouse:
  enabled: true

ollama:
  enabled: true

ingress:
  enabled: false

monitoring:
  enabled: false
EOF
            ;;
    esac
    
    success "Конфигурация подготовлена"
}

# Развертывание Docker Compose
deploy_docker() {
    log "Развертывание через Docker Compose..."
    
    cd infra/compose
    
    # Проверяем что .env файл существует
    if [[ ! -f ".env.local" ]]; then
        error ".env.local файл не найден. Запустите prepare_config."
        exit 1
    fi
    
    # Запускаем сервисы
    export COMPOSE_FILE="docker-compose.yml"
    export COMPOSE_PROJECT_NAME="rag-platform-$ENVIRONMENT"
    
    log "Запуск сервисов..."
    docker compose --env-file .env.local up -d --remove-orphans
    
    # Ждем готовности сервисов
    log "Ожидание готовности сервисов..."
    
    # PostgreSQL
    log "Ожидание PostgreSQL..."
    timeout 60 bash -c 'until docker compose exec postgres pg_isready -U postgres; do sleep 2; done'
    
    # Redis
    log "Ожидание Redis..."
    timeout 30 bash -c 'until docker compose exec redis redis-cli ping; do sleep 2; done'
    
    # API
    log "Ожидание API..."
    timeout 120 bash -c 'until curl -f http://localhost:8081/health &>/dev/null; do sleep 5; done'
    
    # Streamlit
    log "Ожидание Streamlit..."
    timeout 60 bash -c 'until curl -f http://localhost:8502 &>/dev/null; do sleep 5; done'
    
    success "Docker Compose развертывание завершено"
    
    # Показываем URLs
    echo ""
    log "🌐 Доступные сервисы:"
    echo "  • Streamlit Frontend: http://localhost:8502"
    echo "  • API Documentation: http://localhost:8081/docs"
    echo "  • API Health Check: http://localhost:8081/health"
    if docker compose ps | grep -q superset; then
        echo "  • Superset Dashboards: http://localhost:8090"
    fi
    if docker compose ps | grep -q airflow; then
        echo "  • Airflow UI: http://localhost:8080"
    fi
}

# Развертывание Kubernetes
deploy_kubernetes() {
    log "Развертывание в Kubernetes..."
    
    # Применяем манифесты (если они есть)
    if [[ -d "infra/k8s" ]]; then
        kubectl apply -f infra/k8s/ -n $NAMESPACE
    else
        error "Kubernetes манифесты не найдены в infra/k8s/"
        exit 1
    fi
    
    # Ждем готовности
    log "Ожидание готовности подов..."
    kubectl wait --for=condition=ready pod -l app=rag-platform -n $NAMESPACE --timeout=300s
    
    success "Kubernetes развертывание завершено"
    
    # Показываем информацию о сервисах
    echo ""
    log "📋 Статус развертывания:"
    kubectl get pods,svc -n $NAMESPACE
}

# Развертывание Helm
deploy_helm() {
    log "Развертывание через Helm..."
    
    # Добавляем необходимые репозитории
    log "Добавление Helm репозиториев..."
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Устанавливаем/обновляем release
    log "Установка Helm chart..."
    helm upgrade --install rag-platform-$ENVIRONMENT $HELM_CHART \
        --namespace $NAMESPACE \
        --create-namespace \
        --values /tmp/local-values.yaml \
        --timeout 10m \
        --wait
    
    # Ждем готовности
    log "Проверка статуса развертывания..."
    kubectl rollout status deployment/rag-platform-$ENVIRONMENT-api -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/rag-platform-$ENVIRONMENT-streamlit -n $NAMESPACE --timeout=300s
    
    success "Helm развертывание завершено"
    
    # Показываем информацию
    echo ""
    log "📋 Статус Helm release:"
    helm status rag-platform-$ENVIRONMENT -n $NAMESPACE
    
    echo ""
    log "📋 Kubernetes ресурсы:"
    kubectl get all -n $NAMESPACE
}

# Проверочные тесты
run_health_checks() {
    if [[ "$SKIP_TESTS" == true ]]; then
        warning "Проверочные тесты пропущены"
        return
    fi
    
    log "Запуск проверочных тестов..."
    
    case $DEPLOY_METHOD in
        docker)
            # Тестируем API
            log "Проверка API..."
            if curl -f http://localhost:8081/health &>/dev/null; then
                success "API работает"
            else
                error "API недоступен"
                return 1
            fi
            
            # Тестируем Streamlit
            log "Проверка Streamlit..."
            if curl -f http://localhost:8502 &>/dev/null; then
                success "Streamlit работает"
            else
                error "Streamlit недоступен"
                return 1
            fi
            ;;
        kubernetes|helm)
            # Port-forward для тестирования
            log "Настройка port-forward для тестирования..."
            kubectl port-forward svc/rag-platform-$ENVIRONMENT-api 8081:8081 -n $NAMESPACE &
            PF_API_PID=$!
            kubectl port-forward svc/rag-platform-$ENVIRONMENT-streamlit 8502:8502 -n $NAMESPACE &
            PF_STREAMLIT_PID=$!
            
            sleep 5
            
            # Тестируем API
            if curl -f http://localhost:8081/health &>/dev/null; then
                success "API работает"
            else
                error "API недоступен"
            fi
            
            # Тестируем Streamlit
            if curl -f http://localhost:8502 &>/dev/null; then
                success "Streamlit работает"
            else
                error "Streamlit недоступен"
            fi
            
            # Завершаем port-forward
            kill $PF_API_PID $PF_STREAMLIT_PID 2>/dev/null || true
            ;;
    esac
    
    success "Проверочные тесты пройдены"
}

# Показать статус
show_status() {
    echo ""
    log "📊 Статус развертывания RAG Platform:"
    echo "  • Метод: $DEPLOY_METHOD"
    echo "  • Окружение: $ENVIRONMENT"
    echo "  • Namespace: $NAMESPACE"
    echo ""
    
    case $DEPLOY_METHOD in
        docker)
            cd infra/compose
            docker compose ps
            echo ""
            log "💾 Использование ресурсов:"
            docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -10
            ;;
        kubernetes|helm)
            log "🔍 Kubernetes ресурсы:"
            kubectl get all -n $NAMESPACE
            echo ""
            log "💾 Использование ресурсов:"
            kubectl top pods -n $NAMESPACE 2>/dev/null || echo "Metrics server недоступен"
            ;;
    esac
}

# Главная функция
main() {
    echo ""
    log "🚀 Локальное развертывание RAG Platform"
    log "Метод: $DEPLOY_METHOD | Окружение: $ENVIRONMENT"
    echo ""
    
    check_dependencies
    cleanup_deployment
    prepare_images
    prepare_config
    
    case $DEPLOY_METHOD in
        docker)
            deploy_docker
            ;;
        kubernetes)
            deploy_kubernetes
            ;;
        helm)
            deploy_helm
            ;;
        *)
            error "Неизвестный метод развертывания: $DEPLOY_METHOD"
            exit 1
            ;;
    esac
    
    run_health_checks
    show_status
    
    success "Развертывание RAG Platform завершено успешно! 🎉"
    
    echo ""
    log "📚 Полезные команды:"
    case $DEPLOY_METHOD in
        docker)
            echo "  • Логи всех сервисов: cd infra/compose && docker compose logs -f"
            echo "  • Логи API: cd infra/compose && docker compose logs -f api"
            echo "  • Остановка: cd infra/compose && docker compose down"
            echo "  • Полная очистка: cd infra/compose && docker compose down -v"
            ;;
        kubernetes|helm)
            echo "  • Логи: kubectl logs -f deployment/rag-platform-$ENVIRONMENT-api -n $NAMESPACE"
            echo "  • Port-forward API: kubectl port-forward svc/rag-platform-$ENVIRONMENT-api 8081:8081 -n $NAMESPACE"
            echo "  • Port-forward Streamlit: kubectl port-forward svc/rag-platform-$ENVIRONMENT-streamlit 8502:8502 -n $NAMESPACE"
            echo "  • Удаление: kubectl delete namespace $NAMESPACE"
            if [[ "$DEPLOY_METHOD" == "helm" ]]; then
                echo "  • Helm статус: helm status rag-platform-$ENVIRONMENT -n $NAMESPACE"
                echo "  • Helm удаление: helm uninstall rag-platform-$ENVIRONMENT -n $NAMESPACE"
            fi
            ;;
    esac
}

# Обработка сигналов
trap 'error "Развертывание прервано пользователем"; exit 1' INT TERM

# Запуск
main "$@"
