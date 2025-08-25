# 🚀 RAG Platform - Быстрый старт

## ⚡ За 5 минут

### 1. Клонирование и инициализация
```bash
git clone <your-repo-url>
cd Curproject01
make init
```

### 2. Запуск в режиме разработки
```bash
make dev
```

### 3. Открыть в браузере
- **UI**: http://localhost:8501
- **API**: http://localhost:8081/docs

## 🔧 Основные команды

```bash
make help          # Все команды
make dev           # Запуск разработки
make dev-stop      # Остановка
make health        # Проверка системы
make test          # Тесты
make demo          # Демонстрация
```

## 📱 Что можно делать

1. **Загружать документы** - PDF, DOCX, XLSX, HTML, TXT, изображения
2. **Искать по смыслу** - семантический поиск через эмбеддинги
3. **Чат с документами** - RAG с контекстом из загруженных файлов
4. **Анализировать таблицы** - извлечение с сохранением структуры

## 🐳 Docker команды

```bash
# Полный запуск
make build && make up

# Только база данных
docker-compose -f infra/compose/docker-compose.yml up -d postgres redis clickhouse ollama

# Логи
make logs
```

## 🚨 Если что-то не работает

```bash
# Проверка здоровья
make health

# Перезапуск
make dev-stop && make dev

# Очистка
make clean && make init && make build && make up
```

## 📚 Документация

- **Полное руководство**: [README.md](README.md)
- **API документация**: http://localhost:8081/docs
- **Примеры**: [scripts/demo.sh](scripts/demo.sh)

## 🆘 Поддержка

- Создайте Issue для багов
- Проверьте [README.md](README.md) для деталей
- Используйте `make help` для всех команд
