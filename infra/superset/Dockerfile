FROM apache/superset:5.0.0

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка дополнительных пакетов в виртуальное окружение Superset
ENV PYTHONPATH=/app/.venv/lib/python3.10/site-packages:$PYTHONPATH
ENV PIP_TARGET=/app/.venv/lib/python3.10/site-packages
RUN pip install clickhouse-connect psycopg2-binary

USER superset
# Копирование конфигурации и скриптов инициализации
COPY superset_config.py /app/pythonpath/superset_config.py
COPY bootstrap/ /app/superset_bootstrap/

# Создание директории для данных
RUN mkdir -p /app/superset_home

EXPOSE 8088

# Установка переменных окружения
ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py
ENV SUPERSET_HOME=/app/superset_home
