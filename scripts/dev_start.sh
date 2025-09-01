#!/bin/bash

# RAG Platform - Скрипт запуска в режиме разработки

set -e

echo "🚀 Запуск RAG Platform в режиме разработки..."
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}✅${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️${NC} $message"
            ;;
        "error")
            echo -e "${RED}❌${NC} $message"
            ;;
        "info")
            echo -e "${BLUE}ℹ️${NC} $message"
            ;;
    esac
}

# Проверка зависимостей
echo "🔍 Проверка зависимостей..."

if ! command -v docker &> /dev/null; then
    print_status "error" "Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_status "error" "Docker Compose не установлен"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_status "error" "Python3 не установлен"
    exit 1
fi

print_status "success" "Все зависимости доступны"

# Проверка конфигурации
echo ""
echo "⚙️ Проверка конфигурации..."

if [ ! -f "infra/compose/.env.local" ]; then
    print_status "warning" "Файл .env.local не найден, создаю из примера..."
    cp infra/compose/env.example infra/compose/.env.local
    print_status "info" "Отредактируйте infra/compose/.env.local перед запуском"
fi

# Создание необходимых директорий
echo ""
echo "📁 Создание директорий..."
mkdir -p data/inbox uploads backups logs

# Запуск базовых сервисов
echo ""
echo "🐳 Запуск базовых сервисов..."
cd infra/compose

if docker-compose --env-file .env.local up -d postgres redis clickhouse ollama; then
    print_status "success" "Базовые сервисы запущены"
else
    print_status "error" "Ошибка запуска базовых сервисов"
    exit 1
fi

cd ../..

# Ожидание готовности сервисов
echo ""
echo "⏳ Ожидание готовности сервисов..."

wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "   Ожидание $service на порту $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            print_status "success" "$service готов"
            return 0
        fi
        
        echo "   Попытка $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    print_status "error" "$service не готов после $max_attempts попыток"
    return 1
}

wait_for_service "PostgreSQL" 5432
wait_for_service "Redis" 6379
wait_for_service "ClickHouse" 8123

# Проверка Ollama
echo ""
echo "🤖 Проверка Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    print_status "success" "Ollama доступен"
else
    print_status "warning" "Ollama недоступен, проверьте контейнер"
fi

# Установка Python зависимостей
echo ""
echo "🐍 Установка Python зависимостей..."

# API
echo "   Установка зависимостей API..."
cd apps/api
if pip3 install -r requirements.txt; then
    print_status "success" "API зависимости установлены"
else
    print_status "warning" "Ошибка установки API зависимостей"
fi
cd ../..

# Streamlit
echo "   Установка зависимостей Streamlit..."
cd apps/streamlit_app
if pip3 install -r requirements.txt; then
    print_status "success" "Streamlit зависимости установлены"
else
    print_status "warning" "Ошибка установки Streamlit зависимостей"
fi
cd ../..

# Запуск приложений
echo ""
echo "🚀 Запуск приложений..."

# API в фоне
echo "   Запуск API на порту 8081..."
cd apps/api
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8081 --reload &
API_PID=$!
cd ../..

# Streamlit в фоне
echo "   Запуск Streamlit на порту 8502..."
cd apps/streamlit_app
streamlit run src/main.py --server.port 8502 --server.address 0.0.0.0 &
STREAMLIT_PID=$!
cd ../..

# Ожидание запуска приложений
echo ""
echo "⏳ Ожидание запуска приложений..."
sleep 5

# Проверка доступности
echo ""
echo "🔍 Проверка доступности приложений..."

if curl -s http://localhost:8081/health > /dev/null; then
    print_status "success" "API доступен на http://localhost:8081"
else
    print_status "warning" "API недоступен"
fi

if curl -s http://localhost:8502 > /dev/null; then
    print_status "success" "Streamlit доступен на http://localhost:8502"
else
    print_status "warning" "Streamlit недоступен"
fi

# Итоговая информация
echo ""
echo "🎉 RAG Platform запущен в режиме разработки!"
echo ""
echo "📱 Доступные сервисы:"
echo "  - Streamlit UI: http://localhost:8502"
echo "  - API Docs: http://localhost:8081/docs"
echo "  - API Health: http://localhost:8081/health"
echo ""
echo "🐳 Docker сервисы:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - ClickHouse: localhost:8123"
echo "  - Ollama: localhost:11434"
echo ""
echo "🔧 Управление:"
echo "  - Остановка: pkill -f 'uvicorn\|streamlit'"
echo "  - Логи API: tail -f apps/api/logs/app.log"
echo "  - Логи Streamlit: tail -f apps/streamlit_app/logs/app.log"
echo ""
echo "⚠️  Приложения запущены в фоновом режиме"
echo "   PID API: $API_PID"
echo "   PID Streamlit: $STREAMLIT_PID"

# Сохранение PID для последующей остановки
echo "$API_PID" > /tmp/rag_api.pid
echo "$STREAMLIT_PID" > /tmp/rag_streamlit.pid

echo ""
print_status "info" "Для остановки используйте: scripts/dev_stop.sh"
