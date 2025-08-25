"""
Извлечение таблиц для RAG-платформы
Поддерживает Camelot (векторные PDF), Tabula (потоковые PDF), PaddleOCR (сканы)
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logger.warning("camelot-py not available, table extraction disabled")

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    logger.warning("tabula-py not available, table extraction disabled")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR not available, table structure detection disabled")

class TableExtractor:
    """Улучшенный экстрактор таблиц с поддержкой различных методов"""
    
    def __init__(self, 
                 use_camelot: bool = True,
                 use_tabula: bool = True,
                 use_paddle: bool = True):
        self.use_camelot = use_camelot and CAMELOT_AVAILABLE
        self.use_tabula = use_tabula and TABULA_AVAILABLE
        self.use_paddle = use_paddle and PADDLE_AVAILABLE
        
        self._initialize_engines()
        self._check_capabilities()
    
    def _initialize_engines(self):
        """Инициализирует доступные движки"""
        if self.use_paddle:
            try:
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en', 
                    show_log=False,
                    use_gpu=False  # CPU-only для совместимости
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR: {e}")
                self.use_paddle = False
        
        if self.use_camelot:
            logger.info("Camelot-py available for table extraction")
        
        if self.use_tabula:
            logger.info("Tabula-py available for table extraction")
    
    def _check_capabilities(self):
        """Проверяет доступные возможности"""
        capabilities = []
        if self.use_camelot:
            capabilities.append("Camelot (vector PDFs)")
        if self.use_tabula:
            capabilities.append("Tabula (Java-based)")
        if self.use_paddle:
            capabilities.append("PaddleOCR (structure detection)")
        
        logger.info(f"Table extraction capabilities: {', '.join(capabilities)}")
    
    def extract_tables_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы из PDF используя все доступные методы"""
        tables = []
        
        # Метод 1: Camelot (для векторных PDF)
        if self.use_camelot:
            camelot_tables = self._extract_with_camelot(pdf_path)
            tables.extend(camelot_tables)
        
        # Метод 2: Tabula (для сложных таблиц)
        if self.use_tabula:
            tabula_tables = self._extract_with_tabula(pdf_path)
            tables.extend(tabula_tables)
        
        # Метод 3: PaddleOCR (для сканов)
        if self.use_paddle:
            paddle_tables = self._extract_with_paddle(pdf_path)
            tables.extend(paddle_tables)
        
        # Убираем дубликаты и сортируем по качеству
        unique_tables = self._deduplicate_tables(tables)
        sorted_tables = self._sort_tables_by_quality(unique_tables)
        
        logger.info(f"Extracted {len(sorted_tables)} unique tables from {pdf_path}")
        return sorted_tables
    
    def _extract_with_camelot(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы используя Camelot"""
        tables = []
        
        try:
            # Lattice mode (для таблиц с линиями)
            lattice_tables = camelot.read_pdf(
                str(pdf_path), 
                pages='all', 
                flavor='lattice',
                suppress_stdout=True,
                quiet=True
            )
            
            for i, table in enumerate(lattice_tables):
                if table.accuracy > 50:  # Фильтруем по точности
                    table_info = self._process_camelot_table(table, i, 'lattice')
                    tables.append(table_info)
            
            # Stream mode (для таблиц без линий)
            stream_tables = camelot.read_pdf(
                str(pdf_path), 
                pages='all', 
                flavor='stream',
                suppress_stdout=True,
                quiet=True
            )
            
            for i, table in enumerate(stream_tables):
                if table.accuracy > 50 and table.whitespace < 50:
                    table_info = self._process_camelot_table(table, len(tables), 'stream')
                    tables.append(table_info)
                    
        except Exception as e:
            logger.warning(f"Error extracting tables with Camelot from {pdf_path}: {e}")
        
        return tables
    
    def _process_camelot_table(self, table, index: int, method: str) -> Dict[str, Any]:
        """Обрабатывает таблицу Camelot"""
        return {
            'table_index': index,
            'page': table.page,
            'accuracy': table.accuracy,
            'whitespace': table.whitespace,
            'data': table.df.values.tolist(),
            'df': table.df,
            'extraction_method': f'camelot_{method}',
            'bbox': table._bbox,
            'order': table.order,
            'width': table.width,
            'height': table.height
        }
    
    def _extract_with_tabula(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы используя Tabula"""
        tables = []
        
        try:
            # Получаем информацию о страницах
            page_info = tabula.read_pdf(
                str(pdf_path), 
                pages='all', 
                guess=False,
                stream=True,
                pandas_options={'header': None}
            )
            
            for page_num, page_tables in enumerate(page_info):
                if page_tables is not None and not page_tables.empty:
                    # Разбиваем на отдельные таблицы если нужно
                    table_blocks = self._split_tabula_tables(page_tables)
                    
                    for i, table_block in enumerate(table_blocks):
                        table_info = self._process_tabula_table(
                            table_block, 
                            len(tables), 
                            page_num + 1
                        )
                        tables.append(table_info)
                        
        except Exception as e:
            logger.warning(f"Error extracting tables with Tabula from {pdf_path}: {e}")
        
        return tables
    
    def _split_tabula_tables(self, df) -> List:
        """Разбивает результат Tabula на отдельные таблицы"""
        # Простая логика разбиения по пустым строкам
        tables = []
        current_table = []
        
        for idx, row in df.iterrows():
            # Проверяем, является ли строка пустой
            if row.isna().all() or (row == '').all():
                if current_table:
                    tables.append(current_table)
                    current_table = []
            else:
                current_table.append(row)
        
        # Добавляем последнюю таблицу
        if current_table:
            tables.append(current_table)
        
        return tables
    
    def _process_tabula_table(self, table_data, index: int, page: int) -> Dict[str, Any]:
        """Обрабатывает таблицу Tabula"""
        # Конвертируем в список списков
        data = [row.tolist() for row in table_data]
        
        # Очищаем данные
        cleaned_data = []
        for row in data:
            cleaned_row = [str(cell).strip() if cell is not None else '' for cell in row]
            if any(cell for cell in cleaned_row):  # Пропускаем пустые строки
                cleaned_data.append(cleaned_row)
        
        return {
            'table_index': index,
            'page': page,
            'data': cleaned_data,
            'rows': len(cleaned_data),
            'cols': len(cleaned_data[0]) if cleaned_data else 0,
            'extraction_method': 'tabula',
            'accuracy': 80,  # Примерная оценка
            'whitespace': 20
        }
    
    def _extract_with_paddle(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Извлекает таблицы используя PaddleOCR"""
        tables = []
        
        try:
            # Конвертируем PDF в изображения
            images = self._pdf_to_images(pdf_path)
            
            for page_num, image in enumerate(images):
                # Определяем структуру таблицы
                table_structure = self._detect_table_structure(image)
                
                if table_structure:
                    # Извлекаем текст из ячеек
                    table_data = self._extract_table_data_from_image(image, table_structure)
                    
                    table_info = {
                        'table_index': len(tables),
                        'page': page_num + 1,
                        'data': table_data,
                        'rows': len(table_data),
                        'cols': len(table_data[0]) if table_data else 0,
                        'extraction_method': 'paddleocr',
                        'accuracy': 70,  # Примерная оценка для OCR
                        'whitespace': 30,
                        'structure': table_structure
                    }
                    tables.append(table_info)
                    
        except Exception as e:
            logger.warning(f"Error extracting tables with PaddleOCR from {pdf_path}: {e}")
        
        return tables
    
    def _pdf_to_images(self, pdf_path: Path) -> List:
        """Конвертирует PDF в изображения"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(str(pdf_path))
            images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)  # Увеличиваем разрешение
                pix = page.get_pixmap(matrix=mat)
                
                # Конвертируем в PIL Image
                img_data = pix.tobytes("png")
                from PIL import Image
                import io
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
            
            doc.close()
            return images
            
        except ImportError:
            logger.warning("PyMuPDF not available for PDF to image conversion")
            return []
    
    def _detect_table_structure(self, image) -> Optional[Dict[str, Any]]:
        """Определяет структуру таблицы на изображении"""
        if not self.use_paddle:
            return None
        
        try:
            # Конвертируем PIL в numpy для OpenCV
            import numpy as np
            import cv2
            
            if hasattr(image, 'convert'):
                image = image.convert('RGB')
                image_array = np.array(image)
                image_cv = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            else:
                image_cv = image
            
            # PaddleOCR для определения структуры
            result = self.paddle_ocr.ocr(image_cv, cls=True)
            
            if not result or not result[0]:
                return None
            
            # Анализируем результат для определения структуры таблицы
            structure = self._analyze_paddle_result(result[0])
            return structure
            
        except Exception as e:
            logger.warning(f"Error detecting table structure: {e}")
            return None
    
    def _analyze_paddle_result(self, ocr_result: List) -> Dict[str, Any]:
        """Анализирует результат PaddleOCR для определения структуры таблицы"""
        if not ocr_result:
            return {}
        
        # Извлекаем все текстовые блоки
        text_blocks = []
        for line in ocr_result:
            if line:
                bbox, (text, confidence) = line
                text_blocks.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox
                })
        
        if not text_blocks:
            return {}
        
        # Анализируем расположение для определения структуры таблицы
        # Сортируем по Y координате (строки)
        text_blocks.sort(key=lambda x: x['bbox'][0][1])
        
        # Группируем по строкам
        rows = []
        current_row = []
        current_y = None
        y_tolerance = 20  # Допуск для строк
        
        for block in text_blocks:
            y = block['bbox'][0][1]
            
            if current_y is None or abs(y - current_y) <= y_tolerance:
                current_row.append(block)
                current_y = y
            else:
                if current_row:
                    # Сортируем по X координате внутри строки
                    current_row.sort(key=lambda x: x['bbox'][0][0])
                    rows.append(current_row)
                current_row = [block]
                current_y = y
        
        # Добавляем последнюю строку
        if current_row:
            current_row.sort(key=lambda x: x['bbox'][0][0])
            rows.append(current_row)
        
        return {
            'type': 'table',
            'rows': len(rows),
            'max_cols': max(len(row) for row in rows) if rows else 0,
            'cells': [
                {
                    'row': i,
                    'col': j,
                    'text': cell['text'],
                    'confidence': cell['confidence'],
                    'bbox': cell['bbox']
                }
                for i, row in enumerate(rows)
                for j, cell in enumerate(row)
            ]
        }
    
    def _extract_table_data_from_image(self, image, structure: Dict[str, Any]) -> List[List[str]]:
        """Извлекает данные таблицы из изображения на основе структуры"""
        if 'cells' not in structure:
            return []
        
        # Создаем матрицу данных
        max_rows = structure['rows']
        max_cols = structure['max_cols']
        
        # Инициализируем пустую матрицу
        table_data = [['' for _ in range(max_cols)] for _ in range(max_rows)]
        
        # Заполняем данными
        for cell in structure['cells']:
            row = cell['row']
            col = cell['col']
            text = cell['text']
            
            if row < max_rows and col < max_cols:
                table_data[row][col] = text
        
        return table_data
    
    def _deduplicate_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает дубликаты таблиц"""
        unique_tables = []
        seen_content = set()
        
        for table in tables:
            # Создаем хеш содержимого для сравнения
            content_hash = self._create_table_hash(table)
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_tables.append(table)
            else:
                logger.debug(f"Duplicate table found, skipping")
        
        return unique_tables
    
    def _create_table_hash(self, table: Dict[str, Any]) -> str:
        """Создает хеш таблицы для сравнения"""
        data = table.get('data', [])
        if not data:
            return ""
        
        # Создаем строку для хеширования
        content_str = ""
        for row in data:
            for cell in row:
                content_str += str(cell) + "|"
        
        import hashlib
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def _sort_tables_by_quality(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Сортирует таблицы по качеству извлечения"""
        def quality_score(table):
            # Базовый скор
            score = 0
            
            # Точность извлечения
            accuracy = table.get('accuracy', 0)
            score += accuracy * 0.4
            
            # Количество пробелов (меньше = лучше)
            whitespace = table.get('whitespace', 100)
            score += max(0, 100 - whitespace) * 0.3
            
            # Размер таблицы (больше = лучше)
            rows = table.get('rows', 0)
            cols = table.get('cols', 0)
            score += min(rows * cols, 100) * 0.2
            
            # Метод извлечения (приоритет)
            method = table.get('extraction_method', '')
            if 'camelot' in method:
                score += 20
            elif 'tabula' in method:
                score += 15
            elif 'paddleocr' in method:
                score += 10
            
            return score
        
        return sorted(tables, key=quality_score, reverse=True)
    
    def get_extraction_stats(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Возвращает статистику извлечения таблиц"""
        if not tables:
            return {}
        
        methods = {}
        total_accuracy = 0
        total_whitespace = 0
        
        for table in tables:
            method = table.get('extraction_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
            
            total_accuracy += table.get('accuracy', 0)
            total_whitespace += table.get('whitespace', 0)
        
        return {
            'total_tables': len(tables),
            'methods_used': methods,
            'average_accuracy': total_accuracy / len(tables),
            'average_whitespace': total_whitespace / len(tables),
            'best_method': max(methods.items(), key=lambda x: x[1])[0] if methods else 'none'
        }
