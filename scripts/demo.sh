#!/bin/bash

# RAG Platform - Демонстрационный скрипт

echo "🎭 Демонстрация RAG Platform..."
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

# Проверка доступности сервисов
echo "🔍 Проверка доступности сервисов..."

# API
if curl -s http://localhost:8081/health > /dev/null; then
    print_status "success" "API доступен"
else
    print_status "error" "API недоступен. Запустите: make dev"
    exit 1
fi

# Streamlit
if curl -s http://localhost:8501 > /dev/null; then
    print_status "success" "Streamlit доступен"
else
    print_status "error" "Streamlit недоступен. Запустите: make dev"
    exit 1
fi

# Ollama
if curl -s http://localhost:11434/api/tags > /dev/null; then
    print_status "success" "Ollama доступен"
else
    print_status "warning" "Ollama недоступен"
fi

echo ""
echo "🚀 Начинаем демонстрацию..."
echo ""

# Демонстрация API
echo "📡 Демонстрация API..."
echo "1. Проверка здоровья сервиса:"
curl -s http://localhost:8081/health | jq '.' 2>/dev/null || curl -s http://localhost:8081/health

echo ""
echo "2. Список доступных моделей:"
curl -s http://localhost:8081/api/v1/models | jq '.' 2>/dev/null || curl -s http://localhost:8081/api/v1/models

echo ""
echo "3. Статистика платформы:"
curl -s http://localhost:8081/api/v1/stats | jq '.' 2>/dev/null || curl -s http://localhost:8081/api/v1/stats

# Демонстрация поиска
echo ""
echo "🔍 Демонстрация поиска..."
echo "Поиск по запросу 'RAG платформа':"

SEARCH_RESPONSE=$(curl -s -X POST "http://localhost:8081/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "RAG платформа", "top_k": 5}')

if [ $? -eq 0 ]; then
    echo "$SEARCH_RESPONSE" | jq '.' 2>/dev/null || echo "$SEARCH_RESPONSE"
else
    print_status "warning" "Поиск недоступен"
fi

# Демонстрация чата
echo ""
echo "💬 Демонстрация чата..."
echo "Вопрос: 'Что такое RAG платформа?'"

CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8081/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Что такое RAG платформа?", "top_k": 3}')

if [ $? -eq 0 ]; then
    echo "$CHAT_RESPONSE" | jq '.' 2>/dev/null || echo "$CHAT_RESPONSE"
else
    print_status "warning" "Чат недоступен"
fi

# Демонстрация загрузки
echo ""
echo "📤 Демонстрация загрузки..."
echo "Загрузка примера документа..."

UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8081/api/v1/upload" \
  -F "file=@data/inbox/example.txt" \
  -F "title=Пример документа")

if [ $? -eq 0 ]; then
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    print_status "warning" "Загрузка недоступна"
fi

# Демонстрация списка документов
echo ""
echo "📚 Демонстрация списка документов..."
DOCS_RESPONSE=$(curl -s "http://localhost:8081/api/v1/documents?page=1&size=10")

if [ $? -eq 0 ]; then
    echo "$DOCS_RESPONSE" | jq '.' 2>/dev/null || echo "$DOCS_RESPONSE"
else
    print_status "warning" "Список документов недоступен"
fi

echo ""
echo "🎉 Демонстрация завершена!"
echo ""
echo "📱 Веб-интерфейс доступен по адресам:"
echo "  - Streamlit UI: http://localhost:8501"
echo "  - API Docs: http://localhost:8081/docs"
echo ""
echo "🔧 Дополнительные команды:"
echo "  make health     - проверка здоровья системы"
echo "  make test       - запуск тестов"
echo "  make dev-stop   - остановка в режиме разработки"
