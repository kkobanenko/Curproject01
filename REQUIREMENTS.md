# 📋 Требования к системе

## 🖥️ Минимальные требования

### Операционная система
- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **macOS**: 10.15+ (Catalina)
- **Windows**: 10/11 с WSL2

### Аппаратные ресурсы
- **CPU**: 4 ядра (рекомендуется 8+)
- **RAM**: 8 GB (рекомендуется 16+)
- **Диск**: 20 GB свободного места
- **Сеть**: 100 Mbps

### Программное обеспечение
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: 2.30+

## 🐳 Docker требования

### Docker Engine
```bash
# Проверка версии
docker --version
# Должно быть: Docker version 20.10.x или выше
```

### Docker Compose
```bash
# Проверка версии
docker-compose --version
# Должно быть: docker-compose version 2.x.x
```

### Права пользователя
```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
# Перезапустить сессию
newgrp docker
```

## 🐍 Python требования

### Версия Python
```bash
python3 --version
# Должно быть: Python 3.11.x или выше
```

### Менеджер пакетов
```bash
pip3 --version
# Рекомендуется: pip 23.x или выше
```

### Виртуальное окружение (опционально)
```bash
# Создание виртуального окружения
python3 -m venv rag_env
source rag_env/bin/activate  # Linux/macOS
# или
rag_env\Scripts\activate     # Windows
```

## 🌐 Сетевые требования

### Порты
Следующие порты должны быть свободны:
- **8080**: Airflow
- **8081**: API
- **8502**: Streamlit
- **5432**: PostgreSQL
- **6379**: Redis
- **8123**: ClickHouse
- **8088**: Superset
- **11434**: Ollama

### Проверка портов
```bash
# Linux/macOS
netstat -tuln | grep -E ':(8080|8081|8502|5432|6379|8123|8088|11434)'

# Windows
netstat -an | findstr "8080\|8081\|8502\|5432\|6379\|8123\|8088\|11434"
```

## 🔒 Безопасность

### Firewall
```bash
# Ubuntu/Debian
sudo ufw allow 8081/tcp  # API
sudo ufw allow 8502/tcp  # Streamlit

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --permanent --add-port=8502/tcp
sudo firewall-cmd --reload
```

### SELinux (если используется)
```bash
# Временное отключение для тестирования
sudo setenforce 0

# Постоянное отключение
sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```

## 📦 Дополнительные пакеты

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    python3-dev \
    python3-pip \
    python3-venv
```

### CentOS/RHEL
```bash
sudo yum update -y
sudo yum install -y \
    curl \
    wget \
    git \
    gcc \
    gcc-c++ \
    make \
    python3-devel \
    python3-pip
```

### macOS
```bash
# Установка Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка пакетов
brew install \
    curl \
    wget \
    git \
    python@3.11
```

## 🧪 Проверка установки

### Скрипт проверки
```bash
# Запуск проверки здоровья системы
make health

# Или вручную
./scripts/health_check.sh
```

### Тесты
```bash
# Запуск тестов
make test

# Тесты API
make test-api

# Тесты Streamlit
make test-streamlit
```

## 🚨 Решение проблем

### Docker не запускается
```bash
# Проверка статуса
sudo systemctl status docker

# Запуск сервиса
sudo systemctl start docker
sudo systemctl enable docker
```

### Проблемы с портами
```bash
# Поиск процессов на портах
sudo lsof -i :8081
sudo lsof -i :8502

# Остановка процессов
sudo kill -9 <PID>
```

### Проблемы с Python
```bash
# Обновление pip
python3 -m pip install --upgrade pip

# Проверка путей
which python3
which pip3
```

## 📚 Дополнительные ресурсы

- [Docker Installation Guide](https://docs.docker.com/engine/install/)
- [Python Installation](https://www.python.org/downloads/)
- [Git Installation](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Docker Compose Installation](https://docs.docker.com/compose/install/)
