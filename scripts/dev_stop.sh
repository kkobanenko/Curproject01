#!/bin/bash

# RAG Platform - Скрипт остановки в режиме разработки

echo "🛑 Остановка RAG Platform в режиме разработки..."
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

# Остановка API
echo "🔌 Остановка API..."
if [ -f "/tmp/rag_api.pid" ]; then
    API_PID=$(cat /tmp/rag_api.pid)
    if kill -0 "$API_PID" 2>/dev/null; then
        kill "$API_PID"
        print_status "success" "API остановлен (PID: $API_PID)"
    else
        print_status "warning" "API уже остановлен"
    fi
    rm -f /tmp/rag_api.pid
else
    # Попытка найти процесс по имени
    if pkill -f "uvicorn.*src.main:app"; then
        print_status "success" "API остановлен"
    else
        print_status "info" "API не найден"
    fi
fi

# Остановка Streamlit
echo "🔌 Остановка Streamlit..."
if [ -f "/tmp/rag_streamlit.pid" ]; then
    STREAMLIT_PID=$(cat /tmp/rag_streamlit.pid)
    if kill -0 "$STREAMLIT_PID" 2>/dev/null; then
        kill "$STREAMLIT_PID"
        print_status "success" "Streamlit остановлен (PID: $STREAMLIT_PID)"
    else
        print_status "warning" "Streamlit уже остановлен"
    fi
    rm -f /tmp/rag_streamlit.pid
else
    # Попытка найти процесс по имени
    if pkill -f "streamlit.*src.main"; then
        print_status "success" "Streamlit остановлен"
    else
        print_status "info" "Streamlit не найден"
    fi
fi

# Остановка Docker сервисов (опционально)
echo ""
echo "🐳 Остановка Docker сервисов..."
read -p "Остановить Docker сервисы? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd infra/compose
    
    if docker-compose --env-file .env.local down; then
        print_status "success" "Docker сервисы остановлены"
    else
        print_status "warning" "Ошибка остановки Docker сервисов"
    fi
    
    cd ../..
else
    print_status "info" "Docker сервисы оставлены запущенными"
fi

# Очистка временных файлов
echo ""
echo "🧹 Очистка временных файлов..."
rm -f /tmp/rag_*.pid

# Проверка портов
echo ""
echo "🔍 Проверка портов..."

check_port() {
    local port=$1
    local service=$2
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_status "warning" "Порт $port ($service) все еще открыт"
    else
        print_status "success" "Порт $port ($service) закрыт"
    fi
}

check_port 8081 "API"
check_port 8501 "Streamlit"

echo ""
print_status "success" "RAG Platform остановлен"
echo ""
echo "🔧 Для повторного запуска используйте: scripts/dev_start.sh"
