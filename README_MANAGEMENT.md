# 🚀 Управление Streamlit приложением RAG Platform

## 📋 Обзор

Этот документ описывает, как управлять Streamlit приложением RAG Platform, которое предоставляет веб-интерфейс для работы с системой RAG (Retrieval-Augmented Generation).

## 🌐 Доступ к приложению

**URL:** http://localhost:8502

**Демо-аккаунт:**
- **Логин:** `admin`
- **Пароль:** `admin123`

## 🛠️ Скрипт управления

### Основные команды

```bash
# Проверить статус
./manage_streamlit.sh status

# Запустить приложение
./manage_streamlit.sh start

# Остановить приложение
./manage_streamlit.sh stop

# Перезапустить приложение
./manage_streamlit.sh restart

# Проверить доступность
./manage_streamlit.sh health

# Показать информацию о системе
./manage_streamlit.sh info

# Показать последние логи
./manage_streamlit.sh logs

# Интерактивное меню
./manage_streamlit.sh
```

### Интерактивное меню

При запуске без параметров скрипт показывает интерактивное меню:

```
=== RAG Platform ===
Выберите действие:
1) Запустить приложение
2) Остановить приложение
3) Перезапустить приложение
4) Проверить статус
5) Проверить доступность
6) Показать последние логи
7) Показать логи в реальном времени
8) Показать информацию о системе
9) Выход
```

## 📊 Мониторинг

### Проверка статуса
```bash
./manage_streamlit.sh status
```
Показывает, работает ли приложение и на каком порту.

### Проверка доступности
```bash
./manage_streamlit.sh health
```
Проверяет, отвечает ли приложение на HTTP запросы.

### Информация о системе
```bash
./manage_streamlit.sh info
```
Показывает детальную информацию о системе, включая:
- Порт и PID
- Время запуска
- Использование памяти
- Версии Python и Streamlit

## 📝 Логи

### Файл логов
- **Путь:** `streamlit.log`
- **Содержимое:** Все сообщения Streamlit, ошибки и отладочная информация

### Просмотр логов
```bash
# Последние 20 строк
./manage_streamlit.sh logs

# Логи в реальном времени
tail -f streamlit.log

# Поиск ошибок
grep -i error streamlit.log
```

## 🔧 Ручное управление

### Запуск вручную
```bash
streamlit run src/main.py --server.port=8502 --server.address=0.0.0.0
```

### Запуск в фоне
```bash
nohup streamlit run src/main.py --server.port=8502 --server.address=0.0.0.0 > streamlit.log 2>&1 &
```

### Остановка процесса
```bash
# По PID (если известен)
kill <PID>

# По порту
pkill -f "streamlit.*8502"

# Принудительная остановка
pkill -9 -f "streamlit.*8502"
```

## 🚨 Устранение неполадок

### Приложение не запускается

1. **Проверьте порт:**
   ```bash
   lsof -i :8502
   ```

2. **Проверьте логи:**
   ```bash
   tail -f streamlit.log
   ```

3. **Проверьте зависимости:**
   ```bash
   pip list | grep streamlit
   ```

### Приложение не отвечает

1. **Проверьте статус процесса:**
   ```bash
   ./manage_streamlit.sh status
   ```

2. **Проверьте доступность:**
   ```bash
   ./manage_streamlit.sh health
   ```

3. **Проверьте сеть:**
   ```bash
   curl -v http://localhost:8502
   ```

### Проблемы с памятью

1. **Проверьте использование памяти:**
   ```bash
   ./manage_streamlit.sh info
   ```

2. **Перезапустите приложение:**
   ```bash
   ./manage_streamlit.sh restart
   ```

## 📁 Структура файлов

```
apps/streamlit_app/
├── manage_streamlit.sh      # Скрипт управления
├── streamlit.pid           # PID файл процесса
├── streamlit.log           # Логи приложения
├── src/
│   ├── main.py            # Основное приложение
│   └── components/        # Компоненты UI
└── README_MANAGEMENT.md   # Этот файл
```

## 🔒 Безопасность

### Рекомендации
- Не открывайте порт 8502 для внешнего доступа без необходимости
- Используйте HTTPS в продакшн среде
- Регулярно обновляйте зависимости
- Мониторьте логи на предмет подозрительной активности

### Ограничения доступа
```bash
# Ограничить доступ только локальным хостом
streamlit run src/main.py --server.port=8502 --server.address=127.0.0.1
```

## 📈 Производительность

### Мониторинг ресурсов
```bash
# Использование CPU и памяти
top -p $(cat streamlit.pid)

# Сетевые соединения
netstat -tlnp | grep 8502

# Логи производительности
grep -i "performance\|slow\|timeout" streamlit.log
```

### Оптимизация
- Используйте `--server.headless=true` для запуска без браузера
- Настройте логирование уровня INFO или WARNING
- Мониторьте использование памяти и перезапускайте при необходимости

## 🆘 Поддержка

### Полезные команды
```bash
# Полная диагностика
./manage_streamlit.sh info && ./manage_streamlit.sh health

# Перезапуск с очисткой
./manage_streamlit.sh stop && sleep 5 && ./manage_streamlit.sh start

# Просмотр всех процессов Streamlit
ps aux | grep streamlit
```

### Контакты
При возникновении проблем:
1. Проверьте логи: `./manage_streamlit.sh logs`
2. Перезапустите приложение: `./manage_streamlit.sh restart`
3. Обратитесь к документации проекта

---

**RAG Platform** - современная платформа для работы с документами и генерации ответов на основе извлеченной информации.

