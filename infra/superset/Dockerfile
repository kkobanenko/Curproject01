FROM apache/superset:3.0.0

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER superset
# Установка ClickHouse драйвера
RUN pip install clickhouse-connect

COPY superset_config.py /app/pythonpath/superset_config.py
COPY bootstrap/ /app/superset_bootstrap/

EXPOSE 8088
