"""
Главный скрипт инициализации Superset для RAG платформы
"""
import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_database():
    """Ожидание готовности базы данных"""
    logger.info("Waiting for database to be ready...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Добавляем путь к Superset
            sys.path.append('/app')
            from superset import db
            
            # Пробуем подключиться к базе данных
            db.session.execute('SELECT 1')
            logger.info("Database is ready!")
            return True
            
        except Exception as e:
            retry_count += 1
            logger.info(f"Database not ready yet, retry {retry_count}/{max_retries}: {e}")
            time.sleep(2)
    
    logger.error("Database is not ready after maximum retries")
    return False


def run_initialization_scripts():
    """Запуск скриптов инициализации"""
    scripts = [
        'init_superset.py',
        'create_dashboards.py',
        'setup_user.py'
    ]
    
    for script in scripts:
        script_path = f'/app/superset_bootstrap/{script}'
        
        if not os.path.exists(script_path):
            logger.error(f"Script {script_path} not found")
            continue
        
        logger.info(f"Running {script}...")
        
        try:
            # Импортируем и запускаем скрипт
            script_module = script.replace('.py', '')
            exec(f"import {script_module}")
            exec(f"success = {script_module}.main()")
            
            if success:
                logger.info(f"{script} completed successfully")
            else:
                logger.error(f"{script} failed")
                return False
                
        except Exception as e:
            logger.error(f"Error running {script}: {e}")
            return False
    
    return True


def main():
    """Основная функция инициализации"""
    logger.info("Starting Superset initialization for RAG platform...")
    
    # Ждем готовности базы данных
    if not wait_for_database():
        logger.error("Failed to connect to database")
        return False
    
    # Запускаем скрипты инициализации
    if not run_initialization_scripts():
        logger.error("Initialization scripts failed")
        return False
    
    logger.info("Superset initialization completed successfully!")
    logger.info("You can now access Superset at http://localhost:8088")
    logger.info("Login: rag_admin / rag_admin_password")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
