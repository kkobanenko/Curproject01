#!/bin/bash

# RAG Platform - Скрипт проверки здоровья системы

set -e

echo "🏥 Проверка здоровья RAG Platform..."
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

# Проверка Docker
echo "🐳 Проверка Docker..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        print_status "success" "Docker запущен и доступен"
        print_status "info" "Версия: $(docker --version)"
    else
        print_status "error" "Docker не запущен"
        exit 1
    fi
else
    print_status "error" "Docker не установлен"
    exit 1
fi

# Проверка Docker Compose
echo ""
echo "📋 Проверка Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_status "success" "Docker Compose доступен"
    print_status "info" "Версия: $(docker-compose --version)"
else
    print_status "error" "Docker Compose не установлен"
    exit 1
fi

# Проверка Python
echo ""
echo "🐍 Проверка Python..."
if command -v python3 &> /dev/null; then
    print_status "success" "Python3 доступен"
    print_status "info" "Версия: $(python3 --version)"
    
    # Проверка pip
    if command -v pip3 &> /dev/null; then
        print_status "success" "pip3 доступен"
    else
        print_status "warning" "pip3 не найден"
    fi
else
    print_status "error" "Python3 не установлен"
    exit 1
fi

# Проверка Git
echo ""
echo "📚 Проверка Git..."
if command -v git &> /dev/null; then
    print_status "success" "Git доступен"
    print_status "info" "Версия: $(git --version)"
else
    print_status "warning" "Git не установлен"
fi

# Проверка Make
echo ""
echo "🔨 Проверка Make..."
if command -v make &> /dev/null; then
    print_status "success" "Make доступен"
    print_status "info" "Версия: $(make --version | head -n1)"
else
    print_status "warning" "Make не установлен"
fi

# Проверка директорий проекта
echo ""
echo "📁 Проверка структуры проекта..."
required_dirs=(
    "apps/api"
    "apps/streamlit_app"
    "packages/rag_core"
    "infra/compose"
    "configs"
    "scripts"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_status "success" "Директория $dir существует"
    else
        print_status "error" "Директория $dir не найдена"
    fi
done

# Проверка конфигурационных файлов
echo ""
echo "⚙️ Проверка конфигурации..."
required_files=(
    "infra/compose/docker-compose.yml"
    "infra/compose/env.example"
    "configs/app.toml"
    "Makefile"
    "README.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "success" "Файл $file существует"
    else
        print_status "error" "Файл $file не найден"
    fi
done

# Проверка Docker образов
echo ""
echo "🖼️ Проверка Docker образов..."
if docker images | grep -q "rag-platform"; then
    print_status "success" "Образы RAG Platform найдены"
    docker images | grep "rag-platform"
else
    print_status "info" "Образы RAG Platform не найдены (запустите make build)"
fi

# Проверка запущенных контейнеров
echo ""
echo "📦 Проверка запущенных контейнеров..."
if docker ps | grep -q "rag-platform"; then
    print_status "success" "Контейнеры RAG Platform запущены"
    docker ps | grep "rag-platform"
else
    print_status "info" "Контейнеры RAG Platform не запущены (запустите make up)"
fi

# Проверка портов
echo ""
echo "🌐 Проверка портов..."
ports_to_check=(
    "8080:Airflow"
    "8081:API"
    "8502:Streamlit"
    "5432:PostgreSQL"
    "6379:Redis"
    "8123:ClickHouse"
    "8088:Superset"
    "11434:Ollama"
)

for port_info in "${ports_to_check[@]}"; do
    port=$(echo "$port_info" | cut -d: -f1)
    service=$(echo "$port_info" | cut -d: -f2)
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_status "success" "Порт $port ($service) открыт"
    else
        print_status "info" "Порт $port ($service) не открыт"
    fi
done

# Итоговая оценка
echo ""
echo "📊 Итоговая оценка здоровья системы:"

if [ "$(docker ps | grep -c 'rag-platform')" -gt 0 ]; then
    print_status "success" "Система работает"
    echo ""
    echo "🚀 RAG Platform запущен и работает!"
    echo "Доступные сервисы:"
    echo "  - Streamlit UI: http://localhost:8502"
    echo "  - API Docs: http://localhost:8081/docs"
    echo "  - Airflow: http://localhost:8080"
    echo "  - Superset: http://localhost:8088"
else
    print_status "warning" "Система не запущена"
    echo ""
    echo "🔧 Для запуска системы выполните:"
    echo "  make init    - инициализация"
    echo "  make build   - сборка образов"
    echo "  make up      - запуск сервисов"
fi

echo ""
print_status "info" "Проверка здоровья завершена"
