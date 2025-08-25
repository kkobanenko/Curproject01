from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib

from .document_parser import DocumentParser

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available, PDF parsing disabled")

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.warning("camelot-py not available, table extraction disabled")

class PDFParser(DocumentParser):
    """Парсер для PDF файлов с поддержкой таблиц и OCR"""
    
    def __init__(self):
        super().__init__()
        self.supported_mime_types = ['application/pdf']
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Проверяет доступность зависимостей"""
        if not PDF_AVAILABLE:
            logger.error("PyPDF2 not available - PDF parsing will fail")
        if not CAMELOT_AVAILABLE:
            logger.warning("camelot-py not available - table extraction will be limited")
    
    def can_parse(self, file_path: Path) -> bool:
        """Проверяет, может ли парсер обработать PDF файл"""
        return (file_path.suffix.lower() == '.pdf' and 
                file_path.exists() and 
                PDF_AVAILABLE)
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсит PDF документ"""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse file: {file_path}")
        
        # Вычисляем SHA256
        sha256 = self._calculate_sha256(file_path)
        
        # Определяем MIME тип
        mime_type = self.get_mime_type(file_path)
        
        # Парсим содержимое
        content = self._extract_content(file_path)
        
        # Определяем, нужен ли OCR
        needs_ocr = self._needs_ocr(content)
        
        return {
            'title': content.get('title'),
            'text': content.get('text', ''),
            'tables': content.get('tables', []),
            'pages': content.get('pages', []),
            'sha256': sha256,
            'mime_type': mime_type,
            'needs_ocr': needs_ocr,
            'metadata': content.get('metadata', {}),
            'page_count': content.get('page_count', 0),
            'has_tables': len(content.get('tables', [])) > 0
        }
    
    def _extract_content(self, file_path: Path) -> Dict[str, Any]:
        """Извлекает содержимое PDF"""
        content = {
            'text': '',
            'tables': [],
            'pages': [],
            'metadata': {},
            'page_count': 0
        }
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Метаданные
                if pdf_reader.metadata:
                    content['metadata'] = {
                        'title': pdf_reader.metadata.get('/Title'),
                        'author': pdf_reader.metadata.get('/Author'),
                        'subject': pdf_reader.metadata.get('/Subject'),
                        'creator': pdf_reader.metadata.get('/Creator'),
                        'producer': pdf_reader.metadata.get('/Producer'),
                        'creation_date': pdf_reader.metadata.get('/CreationDate'),
                        'modification_date': pdf_reader.metadata.get('/ModDate'),
                    }
                    content['title'] = content['metadata'].get('title')
                
                content['page_count'] = len(pdf_reader.pages)
                
                # Текст по страницам
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    content['text'] += page_text + '\n'
                    content['pages'].append({
                        'page_num': page_num + 1,
                        'text': page_text,
                        'rotation': page.get('/Rotate', 0),
                        'width': page.mediabox.width if hasattr(page, 'mediabox') else None,
                        'height': page.mediabox.height if hasattr(page, 'mediabox') else None
                    })
                
                # Извлекаем таблицы если доступен camelot
                if CAMELOT_AVAILABLE:
                    content['tables'] = self._extract_tables(file_path)
                
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise
        
        return content
    
    def _extract_tables(self, file_path: Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы из PDF используя camelot"""
        tables = []
        
        try:
            # Пробуем lattice mode (для таблиц с линиями)
            lattice_tables = camelot.read_pdf(str(file_path), pages='all', flavor='lattice')
            
            for i, table in enumerate(lattice_tables):
                if table.accuracy > 50:  # Фильтруем по точности
                    tables.append({
                        'table_index': i,
                        'page': table.page,
                        'accuracy': table.accuracy,
                        'whitespace': table.whitespace,
                        'data': table.df.values.tolist(),
                        'df': table.df,
                        'extraction_method': 'lattice'
                    })
            
            # Пробуем stream mode (для таблиц без линий)
            stream_tables = camelot.read_pdf(str(file_path), pages='all', flavor='stream')
            
            for i, table in enumerate(stream_tables):
                if table.accuracy > 50 and table.whitespace < 50:  # Фильтруем по точности и пробелам
                    tables.append({
                        'table_index': len(tables),
                        'page': table.page,
                        'accuracy': table.accuracy,
                        'whitespace': table.whitespace,
                        'data': table.df.values.tolist(),
                        'df': table.df,
                        'extraction_method': 'stream'
                    })
                    
        except Exception as e:
            logger.warning(f"Error extracting tables from PDF {file_path}: {e}")
        
        return tables
    
    def _needs_ocr(self, content: Dict[str, Any]) -> bool:
        """Определяет, нужен ли OCR для документа"""
        text = content.get('text', '')
        page_count = content.get('page_count', 0)
        
        # Если текст очень короткий или отсутствует, возможно это сканы
        if len(text.strip()) < 100:
            return True
        
        # Если много страниц, но мало текста
        if page_count > 1 and len(text.strip()) < page_count * 50:
            return True
        
        return False
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
