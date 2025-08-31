#!/usr/bin/env python3
"""
Полная инициализация Superset для RAG платформы (версия 5.0.0)
"""
import os
import sys
import subprocess
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_command(command, description):
    """Выполнение команды с логированием"""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Success: {description}")
        if result.stdout:
            logger.debug(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in {description}: {e}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False


def wait_for_database():
    """Ожидание готовности базы данных"""
    logger.info("Waiting for database to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            # Проверяем подключение к PostgreSQL
            result = subprocess.run(
                "pg_isready -h postgres -p 5432 -U postgres",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("Database is ready!")
                return True
        except Exception:
            pass
        
        logger.info(f"Database not ready, attempt {attempt + 1}/{max_attempts}")
        time.sleep(2)
    
    logger.error("Database is not ready after maximum attempts")
    return False


def main():
    """Основная функция инициализации"""
    logger.info("Starting complete Superset initialization...")
    
    # Ожидание готовности базы данных
    if not wait_for_database():
        return False
    
    # Обновление схемы базы данных
    if not run_command("superset db upgrade", "Database schema upgrade"):
        return False
    
    # Создание администратора
    if not run_command(
        "superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin",
        "Create admin user"
    ):
        return False
    
    # Инициализация Superset
    if not run_command("superset init", "Superset initialization"):
        return False
    
    # Загрузка примеров (опционально)
    if os.environ.get('SUPERSET_LOAD_EXAMPLES', 'no').lower() == 'yes':
        if not run_command("superset load_examples", "Load example data"):
            return False
    
    # Запуск кастомной инициализации
    logger.info("Running custom initialization...")
    try:
        # Импортируем Flask app для создания контекста
        from superset import create_app
        app = create_app()
        
        with app.app_context():
            from init_superset import main as custom_init
            if not custom_init():
                logger.error("Custom initialization failed")
                return False
    except Exception as e:
        logger.error(f"Error in custom initialization: {e}")
        return False
    
    logger.info("Superset initialization completed successfully!")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
