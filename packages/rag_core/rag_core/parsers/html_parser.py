from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import re

from .document_parser import DocumentParser

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False
    logger.warning("beautifulsoup4 not available, HTML parsing disabled")

class HTMLParser(DocumentParser):
    """Парсер для HTML файлов с поддержкой таблиц и метаданных"""
    
    def __init__(self):
        super().__init__()
        self.supported_mime_types = ['text/html']
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Проверяет доступность зависимостей"""
        if not HTML_AVAILABLE:
            logger.error("beautifulsoup4 not available - HTML parsing will fail")
    
    def can_parse(self, file_path: Path) -> bool:
        """Проверяет, может ли парсер обработать HTML файл"""
        return (file_path.suffix.lower() in ['.html', '.htm'] and 
                file_path.exists() and 
                HTML_AVAILABLE)
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсит HTML документ"""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse file: {file_path}")
        
        # Вычисляем SHA256
        sha256 = self._calculate_sha256(file_path)
        
        # Определяем MIME тип
        mime_type = self.get_mime_type(file_path)
        
        # Парсим содержимое
        content = self._extract_content(file_path)
        
        return {
            'title': content.get('title'),
            'text': content.get('text', ''),
            'tables': content.get('tables', []),
            'pages': content.get('pages', []),
            'sha256': sha256,
            'mime_type': mime_type,
            'needs_ocr': False,  # HTML не нужен OCR
            'metadata': content.get('metadata', {}),
            'table_count': len(content.get('tables', [])),
            'has_tables': len(content.get('tables', [])) > 0,
            'links_count': content.get('links_count', 0),
            'images_count': content.get('images_count', 0)
        }
    
    def _extract_content(self, file_path: Path) -> Dict[str, Any]:
        """Извлекает содержимое HTML"""
        content = {
            'text': '',
            'tables': [],
            'pages': [],
            'metadata': {},
            'links_count': 0,
            'images_count': 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Метаданные
            content['metadata'] = self._extract_metadata(soup)
            content['title'] = content['metadata'].get('title')
            
            # Убираем скрипты и стили
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Извлекаем текст
            content['text'] = self._extract_text(soup)
            
            # Извлекаем таблицы
            content['tables'] = self._extract_tables(soup)
            
            # Считаем ссылки и изображения
            content['links_count'] = len(soup.find_all('a'))
            content['images_count'] = len(soup.find_all('img'))
            
            # Создаем "страницы" для совместимости
            content['pages'] = [{'page_num': 1, 'text': content['text'][:1000] + '...'}]
            
        except Exception as e:
            logger.error(f"Error parsing HTML {file_path}: {e}")
            raise
        
        return content
    
    def _extract_metadata(self, soup) -> Dict[str, Any]:
        """Извлекает метаданные из HTML"""
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                metadata[name] = content
        
        # Open Graph tags
        og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
        for og in og_tags:
            property_name = og.get('property', '')
            content = og.get('content', '')
            if property_name and content:
                metadata[property_name] = content
        
        # Twitter Card tags
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        for twitter in twitter_tags:
            name = twitter.get('name', '')
            content = twitter.get('content', '')
            if name and content:
                metadata[name] = content
        
        # Schema.org structured data
        schema_scripts = soup.find_all('script', type='application/ld+json')
        for script in schema_scripts:
            try:
                import json
                schema_data = json.loads(script.string)
                if isinstance(schema_data, dict):
                    metadata['schema'] = schema_data
                elif isinstance(schema_data, list):
                    metadata['schema'] = schema_data
            except (json.JSONDecodeError, AttributeError):
                pass
        
        return metadata
    
    def _extract_text(self, soup) -> str:
        """Извлекает текст из HTML"""
        # Получаем текст из body
        body = soup.find('body')
        if not body:
            body = soup
        
        # Извлекаем текст по секциям
        text_sections = []
        
        # Заголовки
        for heading in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text_sections.append(heading.get_text().strip())
        
        # Параграфы
        for paragraph in body.find_all('p'):
            text = paragraph.get_text().strip()
            if text:
                text_sections.append(text)
        
        # Списки
        for list_elem in body.find_all(['ul', 'ol']):
            for item in list_elem.find_all('li'):
                text = item.get_text().strip()
                if text:
                    text_sections.append(f"• {text}")
        
        # Div с текстом
        for div in body.find_all('div'):
            text = div.get_text().strip()
            if text and len(text) > 50:  # Только значимые блоки текста
                text_sections.append(text)
        
        return '\n\n'.join(text_sections)
    
    def _extract_tables(self, soup) -> List[Dict[str, Any]]:
        """Извлекает таблицы из HTML"""
        tables = []
        
        for table_index, table in enumerate(soup.find_all('table')):
            table_data = self._extract_table_data(table)
            if table_data:
                table_info = {
                    'table_index': table_index,
                    'data': table_data,
                    'rows': len(table_data),
                    'cols': len(table_data[0]) if table_data else 0,
                    'structure': self._analyze_table_structure(table_data),
                    'html': str(table)
                }
                tables.append(table_info)
        
        return tables
    
    def _extract_table_data(self, table) -> List[List[str]]:
        """Извлекает данные из HTML таблицы"""
        table_data = []
        
        # Обрабатываем строки
        rows = table.find_all('tr')
        for row in rows:
            row_data = []
            
            # Обрабатываем ячейки
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                # Получаем текст из ячейки
                cell_text = cell.get_text(strip=True)
                
                # Обрабатываем объединенные ячейки
                colspan = int(cell.get('colspan', 1))
                for _ in range(colspan):
                    row_data.append(cell_text)
            
            if row_data:  # Добавляем только непустые строки
                table_data.append(row_data)
        
        return table_data
    
    def _analyze_table_structure(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """Анализирует структуру HTML таблицы"""
        if not table_data:
            return {}
        
        rows = len(table_data)
        cols = len(table_data[0]) if table_data else 0
        
        # Определяем заголовки (первая строка)
        headers = table_data[0] if table_data else []
        
        # Анализируем типы данных в колонках
        column_types = []
        for col_idx in range(cols):
            col_data = [row[col_idx] for row in table_data[1:] if col_idx < len(row)]
            col_type = self._infer_column_type(col_data)
            column_types.append(col_type)
        
        return {
            'headers': headers,
            'column_types': column_types,
            'has_merged_cells': False,  # Пока не реализовано
            'is_empty': all(all(not cell for cell in row) for row in table_data)
        }
    
    def _infer_column_type(self, column_data: List[str]) -> str:
        """Определяет тип данных в колонке"""
        if not column_data:
            return 'empty'
        
        # Проверяем на числа
        numeric_count = 0
        date_count = 0
        
        for value in column_data:
            if value.strip():
                # Проверяем на число
                try:
                    float(value.replace(',', '').replace(' ', '').replace('$', '').replace('%', ''))
                    numeric_count += 1
                except ValueError:
                    pass
                
                # Простая проверка на дату
                if any(separator in value for separator in ['/', '-', '.']):
                    if len(value.split()) >= 2:
                        date_count += 1
        
        total_non_empty = len([v for v in column_data if v.strip()])
        
        if total_non_empty == 0:
            return 'empty'
        elif numeric_count / total_non_empty > 0.7:
            return 'numeric'
        elif date_count / total_non_empty > 0.7:
            return 'date'
        else:
            return 'text'
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
