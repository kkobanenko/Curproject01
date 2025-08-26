# 🚀 RAG Platform - Быстрый старт

## 📋 Предварительные требования

- Python 3.8+
- Git
- Доступ к интернету для установки зависимостей

## ⚡ Быстрый запуск

### 1. Клонирование и настройка

```bash
# Клонируем репозиторий
git clone <your-repo-url>
cd Curproject01

# Устанавливаем зависимости
pip install -r apps/api/requirements.txt
pip install -r apps/streamlit_app/requirements.txt
```

### 2. Запуск сервисов

```bash
# Запуск всех сервисов одной командой
./scripts/start_services.sh
```

Или запуск по отдельности:

```bash
# Запуск API (порт 8001)
cd apps/api
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

# В другом терминале - запуск Streamlit (порт 8501)
cd apps/streamlit_app
python3 -m streamlit run src/main.py --server.port 8501 --server.address 0.0.0.0
```

### 3. Доступ к приложениям

- **🌐 Streamlit Frontend**: http://localhost:8501
- **📡 API Backend**: http://localhost:8001
- **📚 API Documentation**: http://localhost:8001/docs

## 🛑 Остановка сервисов

```bash
# Остановка всех сервисов
./scripts/stop_services.sh
```

## 🔧 Устранение неполадок

### Порт уже занят

Если получаете ошибку "Address already in use":

```bash
# Проверяем, что использует порт
lsof -i :8001
lsof -i :8501

# Останавливаем процесс
kill -9 <PID>
```

### Проверка статуса

```bash
# Проверяем, что API работает
curl http://localhost:8001/health

# Проверяем, что Streamlit работает
curl http://localhost:8501/
```

## 📁 Структура проекта

```
Curproject01/
├── apps/
│   ├── api/                 # FastAPI backend
│   └── streamlit_app/       # Streamlit frontend
├── scripts/
│   ├── start_services.sh    # Запуск сервисов
│   └── stop_services.sh     # Остановка сервисов
└── logs/                    # Логи сервисов
```

## 🎯 Основные функции

### API Backend
- ✅ Управление документами
- ✅ Семантический поиск
- ✅ Генерация ответов
- ✅ Аутентификация пользователей

### Streamlit Frontend
- ✅ Загрузка документов
- ✅ Поиск по документам
- ✅ Чат с документами
- ✅ Предпросмотр документов
- ✅ Визуализация таблиц
- ✅ История запросов
- ✅ Экспорт данных
- ✅ Настройки пользователя

## 🔐 Тестирование

Для тестирования API используйте токен: `test_token`

```bash
# Получение списка документов
curl -H "Authorization: Bearer test_token" \
     http://localhost:8001/api/v1/documents/

# Получение содержимого документа
curl -H "Authorization: Bearer test_token" \
     http://localhost:8001/api/v1/documents/doc_1/content
```

## 📝 Логи

Логи сервисов сохраняются в директории `logs/`:
- `logs/api.log` - логи API
- `logs/streamlit.log` - логи Streamlit

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи в директории `logs/`
2. Убедитесь, что все зависимости установлены
3. Проверьте, что порты 8001 и 8501 свободны
4. Перезапустите сервисы с помощью скриптов

---

**🎉 Готово! Теперь у вас работает полнофункциональная RAG Platform!**
