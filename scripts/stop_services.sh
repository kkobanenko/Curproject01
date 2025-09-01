#!/bin/bash

# Скрипт для остановки всех сервисов RAG Platform

echo "🛑 Остановка RAG Platform сервисов..."

# Проверяем, что мы в корневой директории проекта
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Ошибка: запустите скрипт из корневой директории проекта"
    exit 1
fi

# Функция для остановки процесса по порту
stop_service() {
    local port=$1
    local service_name=$2
    
    # Находим PID процесса по порту
    local pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
    
    if [ -n "$pid" ]; then
        echo "🔄 Остановка $service_name (PID: $pid)..."
        kill -TERM $pid
        
        # Ждем завершения
        local count=0
        while [ $count -lt 10 ] && netstat -tln 2>/dev/null | grep ":$port " >/dev/null 2>&1; do
            sleep 1
            count=$((count + 1))
        done
        
        # Принудительная остановка если нужно
        if netstat -tln 2>/dev/null | grep ":$port " >/dev/null 2>&1; then
            echo "⚠️ Принудительная остановка $service_name..."
            kill -KILL $pid
            sleep 1
        fi
        
        if ! netstat -tln 2>/dev/null | grep ":$port " >/dev/null 2>&1; then
            echo "✅ $service_name остановлен"
            return 0
        else
            echo "❌ Не удалось остановить $service_name"
            return 1
        fi
    else
        echo "ℹ️ $service_name не запущен на порту $port"
        return 0
    fi
}

# Останавливаем API
stop_api() {
    stop_service 8001 "API"
}

# Останавливаем Streamlit
stop_streamlit() {
    stop_service 8502 "Streamlit"
}

# Останавливаем все сервисы
echo "🔄 Остановка API..."
stop_api

echo "🔄 Остановка Streamlit..."
stop_streamlit

# Проверяем, что все порты свободны
echo ""
echo "🔍 Проверка статуса сервисов..."

if ! netstat -tln 2>/dev/null | grep ":8001 " >/dev/null 2>&1 && ! netstat -tln 2>/dev/null | grep ":8502 " >/dev/null 2>&1; then
    echo "✅ Все сервисы остановлены"
    echo ""
    echo "📱 Статус портов:"
    echo "   • Порт 8001 (API): свободен"
    echo "   • Порт 8502 (Streamlit): свободен"
else
    echo "⚠️ Некоторые сервисы все еще запущены:"
    
    if netstat -tln 2>/dev/null | grep ":8001 " >/dev/null 2>&1; then
        echo "   • API все еще работает на порту 8001"
    fi
    
    if netstat -tln 2>/dev/null | grep ":8502 " >/dev/null 2>&1; then
        echo "   • Streamlit все еще работает на порту 8502"
    fi
    
    echo ""
    echo "💡 Для принудительной остановки используйте:"
    echo "   sudo netstat -tlnp | grep ':8001 ' | awk '{print \$7}' | cut -d'/' -f1 | xargs kill -KILL"
    echo "   sudo netstat -tlnp | grep ':8502 ' | awk '{print \$7}' | cut -d'/' -f1 | xargs kill -KILL"
fi

echo ""
echo "🔄 Для запуска сервисов используйте: ./scripts/start_services.sh"
