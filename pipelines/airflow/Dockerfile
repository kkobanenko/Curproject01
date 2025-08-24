FROM apache/airflow:2.9.3

USER root

# Системные зависимости для OCR/таблиц
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    default-jre-headless \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Python-зависимости будут устанавливаться на этапе airflow-init из requirements.txt
