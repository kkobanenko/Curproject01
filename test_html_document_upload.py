#!/usr/bin/env python3
"""
Финальный тест загрузки HTML документа
Демонстрирует полную функциональность обработки HTML файла
"""

import asyncio
import sys
import logging
from pathlib import Path
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_html_document_processing():
    """Тестирует полную обработку HTML документа"""
    try:
        # Импортируем модули напрямую
        import importlib.util
        from pathlib import Path
        
        # Импортируем DocumentParser
        spec = importlib.util.spec_from_file_location(
            "document_parser", 
            Path(__file__).parent / "packages" / "rag_core" / "rag_core" / "parsers" / "document_parser.py"
        )
        document_parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(document_parser_module)
        DocumentParser = document_parser_module.DocumentParser
        DocumentParserRegistry = document_parser_module.DocumentParserRegistry
        
        # Создаем HTML парсер
        class HTMLParser(DocumentParser):
            def __init__(self):
                super().__init__()
                self.supported_mime_types = ['text/html']
            
            def can_parse(self, file_path: Path) -> bool:
                return (file_path.suffix.lower() in ['.html', '.htm'] and 
                        file_path.exists())
            
            def parse(self, file_path: Path):
                from bs4 import BeautifulSoup
                import hashlib
                
                # Вычисляем SHA256
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                sha256 = sha256_hash.hexdigest()
                
                # Читаем файл
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    html_content = file.read()
                
                # Парсим с BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Извлекаем метаданные
                metadata = {}
                title_tag = soup.find('title')
                if title_tag:
                    metadata['title'] = title_tag.get_text().strip()
                
                # Убираем скрипты и стили
                for script in soup(["script", "style", "noscript"]):
                    script.decompose()
                
                # Извлекаем текст
                text_sections = []
                for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    text_sections.append(heading.get_text().strip())
                
                for paragraph in soup.find_all('p'):
                    text = paragraph.get_text().strip()
                    if text:
                        text_sections.append(text)
                
                full_text = '\n\n'.join(text_sections)
                
                # Извлекаем таблицы
                tables = []
                for table_index, table in enumerate(soup.find_all('table')):
                    table_data = []
                    rows = table.find_all('tr')
                    for row in rows:
                        row_data = []
                        cells = row.find_all(['td', 'th'])
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            row_data.append(cell_text)
                        if row_data:
                            table_data.append(row_data)
                    
                    if table_data:
                        table_info = {
                            'table_index': table_index,
                            'data': table_data,
                            'rows': len(table_data),
                            'cols': len(table_data[0]) if table_data else 0
                        }
                        tables.append(table_info)
                
                # Считаем ссылки и изображения
                links_count = len(soup.find_all('a'))
                images_count = len(soup.find_all('img'))
                
                return {
                    'title': metadata.get('title', 'Без заголовка'),
                    'text': full_text,
                    'tables': tables,
                    'pages': [{'page_num': 1, 'text': full_text[:1000] + '...'}],
                    'sha256': sha256,
                    'mime_type': 'text/html',
                    'needs_ocr': False,
                    'metadata': metadata,
                    'table_count': len(tables),
                    'has_tables': len(tables) > 0,
                    'links_count': links_count,
                    'images_count': images_count
                }
        
        # Создаем registry и регистрируем парсер
        registry = DocumentParserRegistry()
        html_parser = HTMLParser()
        registry.register(html_parser)
        
        # Путь к HTML файлу
        html_file = Path("data/inbox/Смирягин Андрей. Аппетитный прыщик - royallib.ru.html")
        
        if not html_file.exists():
            logger.error(f"HTML файл не найден: {html_file}")
            return False
        
        logger.info(f"🔍 Обрабатываем HTML документ: {html_file}")
        
        # Находим подходящий парсер
        parser = registry.get_parser(html_file)
        if not parser:
            logger.error(f"Не найден подходящий парсер для файла: {html_file}")
            return False
        
        logger.info(f"✅ Найден парсер: {parser.__class__.__name__}")
        
        # Парсим файл
        result = parser.parse(html_file)
        
        # Создаем документ для загрузки
        document_info = {
            'id': f"doc_{result['sha256'][:8]}",
            'title': result.get('title', 'Без заголовка'),
            'source_path': str(html_file),
            'mime_type': result.get('mime_type', 'text/html'),
            'sha256': result.get('sha256', ''),
            'size_bytes': html_file.stat().st_size,
            'tenant_id': 'default',
            'created_at': datetime.utcnow().isoformat(),
            'metadata': {
                'description': 'HTML документ с книгой',
                'tags': ['книга', 'литература', 'html'],
                'original_filename': html_file.name,
                'processing_info': {
                    'parser': parser.__class__.__name__,
                    'processed_at': datetime.utcnow().isoformat(),
                    'text_length': len(result.get('text', '')),
                    'tables_count': result.get('table_count', 0),
                    'links_count': result.get('links_count', 0),
                    'images_count': result.get('images_count', 0)
                }
            },
            'chunk_count': 0,  # Будет заполнено после чанкинга
            'status': 'processed'
        }
        
        logger.info(f"✅ Документ успешно обработан")
        logger.info(f"   - Document ID: {document_info['id']}")
        logger.info(f"   - Заголовок: {document_info['title']}")
        logger.info(f"   - Размер файла: {document_info['size_bytes']} байт")
        logger.info(f"   - Длина текста: {len(result.get('text', ''))}")
        logger.info(f"   - Количество таблиц: {result.get('table_count', 0)}")
        logger.info(f"   - Количество ссылок: {result.get('links_count', 0)}")
        logger.info(f"   - SHA256: {result.get('sha256', '')[:16]}...")
        
        # Показываем первые 300 символов текста
        text = result.get('text', '')
        if text:
            logger.info(f"   - Начало текста: {text[:300]}...")
        
        # Сохраняем результат в JSON файл
        output_file = Path("data/processed_html_document.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'document_info': document_info,
                'parsed_content': result,
                'processing_timestamp': datetime.utcnow().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Результат сохранен в: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке документа: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_validation():
    """Тестирует валидацию обработанного документа"""
    try:
        output_file = Path("data/processed_html_document.json")
        
        if not output_file.exists():
            logger.error(f"Файл с результатом не найден: {output_file}")
            return False
        
        logger.info(f"🔍 Валидируем обработанный документ: {output_file}")
        
        # Читаем результат
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        document_info = data.get('document_info', {})
        parsed_content = data.get('parsed_content', {})
        
        # Проверяем обязательные поля
        required_fields = ['id', 'title', 'source_path', 'mime_type', 'sha256', 'size_bytes']
        for field in required_fields:
            if field not in document_info:
                logger.error(f"❌ Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем SHA256
        if len(document_info['sha256']) != 64:
            logger.error(f"❌ Неверный формат SHA256: {document_info['sha256']}")
            return False
        
        # Проверяем размер файла
        if document_info['size_bytes'] <= 0:
            logger.error(f"❌ Неверный размер файла: {document_info['size_bytes']}")
            return False
        
        # Проверяем MIME тип
        if document_info['mime_type'] != 'text/html':
            logger.error(f"❌ Неверный MIME тип: {document_info['mime_type']}")
            return False
        
        logger.info(f"✅ Документ прошел валидацию")
        logger.info(f"   - Все обязательные поля присутствуют")
        logger.info(f"   - SHA256 корректен")
        logger.info(f"   - Размер файла: {document_info['size_bytes']} байт")
        logger.info(f"   - MIME тип: {document_info['mime_type']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при валидации документа: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция"""
    logger.info("🧪 Начинаем финальное тестирование загрузки HTML документа")
    
    tests = [
        ("HTML Document Processing", test_html_document_processing),
        ("Document Validation", test_document_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Тестируем {test_name} ---")
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name} прошел успешно")
        else:
            logger.error(f"❌ {test_name} не прошел")
    
    logger.info(f"\n📊 Результаты: {passed}/{total} тестов прошли")
    
    if passed == total:
        logger.info("🎉 Все тесты прошли успешно!")
        logger.info("✅ HTML документ успешно обработан и готов к загрузке в систему")
        logger.info("📁 Результат сохранен в data/processed_html_document.json")
        return 0
    else:
        logger.error("⚠️ Некоторые тесты не прошли")
        return 1

if __name__ == "__main__":
    sys.exit(main())
