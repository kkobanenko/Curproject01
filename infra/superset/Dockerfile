FROM apache/superset:3.0.0

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER superset
COPY superset_config.py /app/pythonpath/superset_config.py

EXPOSE 8088
