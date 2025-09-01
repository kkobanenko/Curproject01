#!/bin/bash

# Скрипт для запуска всех сервисов RAG Platform

echo "🚀 Запуск RAG Platform сервисов..."

# Проверяем, что мы в корневой директории проекта
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Ошибка: запустите скрипт из корневой директории проекта"
    exit 1
fi

# Функция для проверки доступности порта
check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tln 2>/dev/null | grep ":$port " >/dev/null 2>&1; then
        echo "✅ $service_name уже запущен на порту $port"
        return 0
    else
        echo "❌ $service_name не запущен на порту $port"
        return 1
    fi
}

# Функция для запуска API
start_api() {
    if check_port 8001 "API"; then
        return 0
    fi
    
    echo "🔧 Запуск API на порту 8001..."
    cd apps/api
    nohup python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload > ../../logs/api.log 2>&1 &
    cd ../..
    
    # Ждем запуска
    sleep 3
    
    if check_port 8001 "API"; then
        echo "✅ API успешно запущен на порту 8001"
        return 0
    else
        echo "❌ Не удалось запустить API"
        return 1
    fi
}

# Функция для запуска Streamlit
start_streamlit() {
    if check_port 8502 "Streamlit"; then
        return 0
    fi
    
    echo "🔧 Запуск Streamlit на порту 8502..."
    cd apps/streamlit_app
    nohup python3 -m streamlit run src/main.py --server.port 8502 --server.address 0.0.0.0 > ../../logs/streamlit.log 2>&1 &
    cd ../..
    
    # Ждем запуска
    sleep 5
    
    if check_port 8502 "Streamlit"; then
        echo "✅ Streamlit успешно запущен на порту 8502"
        return 0
    else
        echo "❌ Не удалось запустить Streamlit"
        return 1
    fi
}

# Создаем директорию для логов
mkdir -p logs

# Запускаем API
if start_api; then
    echo "📡 API доступен по адресу: http://localhost:8001"
    echo "📚 Документация API: http://localhost:8001/docs"
else
    echo "❌ Не удалось запустить API"
    exit 1
fi

# Запускаем Streamlit
if start_streamlit; then
    echo "🌐 Streamlit доступен по адресу: http://localhost:8502"
else
    echo "❌ Не удалось запустить Streamlit"
    exit 1
fi

echo ""
echo "🎉 Все сервисы запущены!"
echo ""
echo "📱 Доступные сервисы:"
echo "   • API: http://localhost:8001"
echo "   • API Docs: http://localhost:8001/docs"
echo "   • Streamlit: http://localhost:8502"
echo ""
echo "📋 Логи сервисов:"
echo "   • API: logs/api.log"
echo "   • Streamlit: logs/streamlit.log"
echo ""
echo "🛑 Для остановки всех сервисов используйте: ./scripts/stop_services.sh"
