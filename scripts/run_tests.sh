#!/bin/bash

# RAG Platform - Скрипт запуска тестов

set -e

echo "🧪 Запуск тестов RAG Platform..."
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    esac
}

# Проверка Python
if ! command -v python3 &> /dev/null; then
    print_status "error" "Python3 не установлен"
    exit 1
fi

print_status "success" "Python3 найден: $(python3 --version)"

# Тестирование API
echo ""
echo "🔍 Тестирование API..."
cd apps/api

if python3 test_basic.py; then
    print_status "success" "API тесты пройдены"
else
    print_status "error" "API тесты не пройдены"
    API_TESTS_FAILED=true
fi

cd ../..

# Тестирование Streamlit
echo ""
echo "🔍 Тестирование Streamlit..."
cd apps/streamlit_app

if python3 test_basic.py; then
    print_status "success" "Streamlit тесты пройдены"
else
    print_status "error" "Streamlit тесты не пройдены"
    STREAMLIT_TESTS_FAILED=true
fi

cd ../..

# Итоговый результат
echo ""
echo "📊 Итоговые результаты:"

if [ "$API_TESTS_FAILED" = true ] || [ "$STREAMLIT_TESTS_FAILED" = true ]; then
    print_status "error" "Некоторые тесты не пройдены"
    echo ""
    echo "🔧 Рекомендации:"
    echo "1. Проверьте установку зависимостей: pip install -r requirements.txt"
    echo "2. Убедитесь, что все модули импортируются корректно"
    echo "3. Проверьте синтаксис Python файлов"
    exit 1
else
    print_status "success" "Все тесты пройдены успешно!"
    echo ""
    echo "🚀 Проект готов к запуску!"
    echo "Используйте команды:"
    echo "  make init    - инициализация проекта"
    echo "  make build   - сборка образов"
    echo "  make up      - запуск сервисов"
fi
