#!/bin/bash

# Скрипт для запуска тестов RAG Platform API
# Поддерживает различные типы тестов и отчеты

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция вывода с цветом
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

# Значения по умолчанию
TEST_TYPE="all"
COVERAGE=true
HTML_REPORT=false
PARALLEL=false
VERBOSE=false
MARKERS=""
CLEAN=false

# Функция помощи
show_help() {
    cat << EOF
Скрипт запуска тестов RAG Platform API

ИСПОЛЬЗОВАНИЕ:
    ./run_tests.sh [ОПЦИИ]

ОПЦИИ:
    -t, --type TYPE        Тип тестов: unit|integration|e2e|load|all (по умолчанию: all)
    -c, --coverage         Включить отчет покрытия кода (по умолчанию: включено)
    -h, --html            Создать HTML отчет покрытия
    -p, --parallel        Запуск тестов параллельно
    -v, --verbose         Подробный вывод
    -m, --markers MARKERS  Дополнительные маркеры pytest
    --clean               Очистить кэш pytest перед запуском
    --help                Показать эту справку

ПРИМЕРЫ:
    ./run_tests.sh                              # Все тесты с покрытием
    ./run_tests.sh -t unit -v                   # Unit тесты с подробным выводом
    ./run_tests.sh -t integration -p            # Integration тесты параллельно
    ./run_tests.sh -t load --clean              # Нагрузочные тесты с очисткой кэша
    ./run_tests.sh -h -p                       # Все тесты с HTML отчетом параллельно
    ./run_tests.sh -m "not slow"               # Все тесты кроме медленных

МАРКЕРЫ ТЕСТОВ:
    unit          - Unit тесты (быстрые, изолированные)
    integration   - Integration тесты (взаимодействие компонентов)
    e2e           - End-to-end тесты (полные сценарии)
    load          - Нагрузочные тесты (производительность)
    slow          - Медленные тесты (>1 секунды)
    database      - Тесты требующие БД
    redis         - Тесты требующие Redis
    external      - Тесты требующие внешние сервисы
EOF
}

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--html)
            HTML_REPORT=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        --clean)
            CLEAN=true
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
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 не найден"
        exit 1
    fi
    
    if ! python3 -c "import pytest" &> /dev/null; then
        error "pytest не установлен. Установите зависимости: pip install -r requirements.txt"
        exit 1
    fi
    
    success "Зависимости проверены"
}

# Очистка кэша
clean_cache() {
    if [[ "$CLEAN" == true ]]; then
        log "Очистка кэша pytest..."
        rm -rf .pytest_cache/
        rm -rf __pycache__/
        find . -name "*.pyc" -delete
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        success "Кэш очищен"
    fi
}

# Построение команды pytest
build_pytest_command() {
    local cmd="python3 -m pytest"
    
    # Тип тестов
    case $TEST_TYPE in
        unit)
            cmd="$cmd -m unit"
            ;;
        integration)
            cmd="$cmd -m integration"
            ;;
        e2e)
            cmd="$cmd -m e2e"
            ;;
        load)
            cmd="$cmd -m load"
            ;;
        all)
            # Запускаем все тесты
            ;;
        *)
            error "Неизвестный тип тестов: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Дополнительные маркеры
    if [[ -n "$MARKERS" ]]; then
        if [[ "$cmd" == *"-m "* ]]; then
            cmd="$cmd and $MARKERS"
        else
            cmd="$cmd -m \"$MARKERS\""
        fi
    fi
    
    # Покрытие кода
    if [[ "$COVERAGE" == true ]]; then
        cmd="$cmd --cov=src --cov-report=term-missing"
        
        if [[ "$HTML_REPORT" == true ]]; then
            cmd="$cmd --cov-report=html:htmlcov"
        fi
        
        cmd="$cmd --cov-report=xml:coverage.xml"
    fi
    
    # Параллельное выполнение
    if [[ "$PARALLEL" == true ]]; then
        # Определяем количество CPU
        if command -v nproc &> /dev/null; then
            local cpu_count=$(nproc)
        else
            local cpu_count=4  # Значение по умолчанию
        fi
        cmd="$cmd -n $cpu_count"
    fi
    
    # Подробный вывод
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd -v"
    else
        cmd="$cmd --tb=short"
    fi
    
    # Дополнительные опции
    cmd="$cmd --strict-markers --strict-config"
    
    echo "$cmd"
}

# Запуск тестов
run_tests() {
    local pytest_cmd=$(build_pytest_command)
    
    log "Запуск тестов..."
    log "Команда: $pytest_cmd"
    log "Тип тестов: $TEST_TYPE"
    
    if [[ "$COVERAGE" == true ]]; then
        log "Покрытие кода: включено"
    fi
    
    if [[ "$PARALLEL" == true ]]; then
        log "Параллельное выполнение: включено"
    fi
    
    echo ""
    
    # Запускаем тесты
    if eval $pytest_cmd; then
        success "Тесты завершены успешно!"
        
        # Показываем результаты покрытия
        if [[ "$COVERAGE" == true ]] && [[ -f "coverage.xml" ]]; then
            log "Анализ покрытия кода..."
            python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    line_rate = float(root.attrib.get('line-rate', 0)) * 100
    branch_rate = float(root.attrib.get('branch-rate', 0)) * 100
    print(f'📊 Общее покрытие: {line_rate:.1f}%')
    print(f'🌿 Покрытие ветвлений: {branch_rate:.1f}%')
    
    if line_rate >= 80:
        print('✅ Покрытие соответствует требованиям (≥80%)')
    else:
        print(f'⚠️  Покрытие ниже требуемого уровня (80%)')
except Exception as e:
    print(f'❌ Ошибка анализа покрытия: {e}')
"
        fi
        
        # HTML отчет
        if [[ "$HTML_REPORT" == true ]] && [[ -d "htmlcov" ]]; then
            success "HTML отчет создан: htmlcov/index.html"
        fi
        
        return 0
    else
        error "Тесты завершились с ошибками!"
        return 1
    fi
}

# Генерация отчета
generate_report() {
    if [[ "$COVERAGE" == true ]]; then
        log "Генерация итогового отчета..."
        
        cat << EOF

================================================================================
📋 ОТЧЕТ О ТЕСТИРОВАНИИ
================================================================================

📅 Дата: $(date +'%Y-%m-%d %H:%M:%S')
🔧 Тип тестов: $TEST_TYPE
📊 Покрытие кода: $([ "$COVERAGE" == true ] && echo "включено" || echo "отключено")
⚡ Параллельное выполнение: $([ "$PARALLEL" == true ] && echo "включено" || echo "отключено")

EOF

        if [[ -f "coverage.xml" ]]; then
            python3 -c "
import xml.etree.ElementTree as ET
import sys

try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    
    line_rate = float(root.attrib.get('line-rate', 0)) * 100
    branch_rate = float(root.attrib.get('branch-rate', 0)) * 100
    
    print('📈 ПОКРЫТИЕ КОДА:')
    print(f'   • Общее покрытие: {line_rate:.1f}%')
    print(f'   • Покрытие ветвлений: {branch_rate:.1f}%')
    print()
    
    # Статус качества
    if line_rate >= 90:
        print('🏆 Отличное качество кода!')
    elif line_rate >= 80:
        print('✅ Хорошее качество кода')
    elif line_rate >= 70:
        print('⚠️  Удовлетворительное качество кода')
    else:
        print('❌ Требуется улучшение покрытия')
        
except Exception as e:
    print(f'❌ Ошибка анализа: {e}')
    sys.exit(1)
"
        fi
        
        echo ""
        echo "================================================================================"
    fi
}

# Основная функция
main() {
    echo ""
    log "🧪 Запуск тестов RAG Platform API"
    echo ""
    
    check_dependencies
    clean_cache
    
    if run_tests; then
        generate_report
        success "Тестирование завершено успешно! 🎉"
        exit 0
    else
        error "Тестирование завершилось с ошибками!"
        exit 1
    fi
}

# Запуск
main "$@"
