FROM python:3.11-slim

WORKDIR /app

# Копируем только код приложения
COPY src/ ./src/

EXPOSE 8501

# Используем стандартную библиотеку Python
CMD ["python", "src/main.py"]
