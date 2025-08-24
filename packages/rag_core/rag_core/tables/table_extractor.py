"""
Извлечение таблиц для RAG-платформы
Поддерживает Camelot (векторные PDF), Tabula (потоковые PDF), PaddleOCR (сканы)
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd

# Импорты для различных методов извлечения таблиц
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logging.warning("camelot-py not available, PDF table extraction disabled")

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    logging.warning("tabula-py not available, PDF table extraction disabled")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logging.warning("PaddleOCR not available, image table extraction disabled")

@dataclass
class TableData:
    """Данные таблицы"""
    data: List[List[str]]
    rows: int
    cols: int
    page: Optional[int] = None
    bbox: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    extraction_method: str = "unknown"
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TableExtractionResult:
    """Результат извлечения таблиц"""
    tables: List[TableData]
    total_tables: int
    extraction_methods_used: List[str]
    success_rate: float

class TableExtractor:
    """Основной экстрактор таблиц"""
    
    def __init__(self):
        self.camelot_available = CAMELOT_AVAILABLE
        self.tabula_available = TABULA_AVAILABLE
        self.paddle_available = PADDLE_AVAILABLE
        
        if self.paddle_available:
            try:
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
                logging.info("PaddleOCR initialized for table extraction")
            except Exception as e:
                logging.warning(f"PaddleOCR not available: {e}")
                self.paddle_available = False
    
    def extract_tables(self, content: Any) -> TableExtractionResult:
        """Извлечение таблиц из контента документа"""
        # Здесь будет логика обработки DocumentContent
        # Пока заглушка
        return TableExtractionResult(
            tables=[],
            total_tables=0,
            extraction_methods_used=[],
            success_rate=0.0
        )
    
    def extract_from_pdf(self, pdf_path: str, method: str = "auto") -> TableExtractionResult:
        """Извлечение таблиц из PDF"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if method == "auto":
            # Автоматически выбираем лучший метод
            return self._extract_from_pdf_auto(pdf_path)
        elif method == "camelot" and self.camelot_available:
            return self._extract_with_camelot(pdf_path)
        elif method == "tabula" and self.tabula_available:
            return self._extract_with_tabula(pdf_path)
        elif method == "paddle" and self.paddle_available:
            return self._extract_with_paddle(pdf_path)
        else:
            raise ValueError(f"Unsupported extraction method: {method}")
    
    def extract_from_image(self, image_path: str) -> TableExtractionResult:
        """Извлечение таблиц из изображения"""
        if not self.paddle_available:
            raise ImportError("PaddleOCR not available for image table extraction")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            tables = []
            extraction_methods = ["paddle"]
            
            # Извлекаем таблицы с помощью PaddleOCR
            table_data = self._extract_table_structure_paddle(image_path)
            
            if table_data and table_data.get('structure', {}).get('type') == 'table':
                structure = table_data['structure']
                
                # Преобразуем в формат TableData
                table = TableData(
                    data=structure.get('cells', []),
                    rows=structure.get('rows', 0),
                    cols=structure.get('max_cols', 0),
                    confidence=0.8,  # Примерная оценка
                    extraction_method="paddle",
                    metadata={
                        'orientation': table_data.get('orientation', 0),
                        'bbox': table_data.get('bbox')
                    }
                )
                tables.append(table)
            
            success_rate = len(tables) / 1.0 if tables else 0.0
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                extraction_methods_used=extraction_methods,
                success_rate=success_rate
            )
            
        except Exception as e:
            logging.error(f"Error extracting tables from image {image_path}: {e}")
            raise
    
    def _extract_from_pdf_auto(self, pdf_path: str) -> TableExtractionResult:
        """Автоматический выбор метода извлечения для PDF"""
        all_tables = []
        methods_used = []
        
        # Пробуем Camelot (лучше для векторных PDF)
        if self.camelot_available:
            try:
                camelot_result = self._extract_with_camelot(pdf_path)
                if camelot_result.tables:
                    all_tables.extend(camelot_result.tables)
                    methods_used.append("camelot")
                    logging.info(f"Extracted {len(camelot_result.tables)} tables with Camelot")
            except Exception as e:
                logging.warning(f"Camelot extraction failed: {e}")
        
        # Пробуем Tabula (лучше для потоковых PDF)
        if self.tabula_available:
            try:
                tabula_result = self._extract_with_tabula(pdf_path)
                if tabula_result.tables:
                    all_tables.extend(tabula_result.tables)
                    methods_used.append("tabula")
                    logging.info(f"Extracted {len(tabula_result.tables)} tables with Tabula")
            except Exception as e:
                logging.warning(f"Tabula extraction failed: {e}")
        
        # Если ничего не получилось, пробуем PaddleOCR
        if not all_tables and self.paddle_available:
            try:
                paddle_result = self._extract_with_paddle(pdf_path)
                if paddle_result.tables:
                    all_tables.extend(paddle_result.tables)
                    methods_used.append("paddle")
                    logging.info(f"Extracted {len(paddle_result.tables)} tables with PaddleOCR")
            except Exception as e:
                logging.warning(f"PaddleOCR extraction failed: {e}")
        
        success_rate = len(all_tables) / max(len(methods_used), 1)
        
        return TableExtractionResult(
            tables=all_tables,
            total_tables=len(all_tables),
            extraction_methods_used=methods_used,
            success_rate=success_rate
        )
    
    def _extract_with_camelot(self, pdf_path: str) -> TableExtractionResult:
        """Извлечение таблиц с помощью Camelot"""
        if not self.camelot_available:
            raise ImportError("Camelot not available")
        
        try:
            # Пробуем разные методы Camelot
            tables = []
            methods_used = ["camelot"]
            
            # Lattice mode (для таблиц с линиями)
            try:
                lattice_tables = camelot.read_pdf(
                    pdf_path, 
                    pages='all', 
                    flavor='lattice',
                    suppress_stdout=True
                )
                
                for table in lattice_tables:
                    if table.parsing_report['accuracy'] > 80:  # Фильтруем по точности
                        table_data = TableData(
                            data=table.df.values.tolist(),
                            rows=len(table.df),
                            cols=len(table.df.columns),
                            page=table.page,
                            bbox=table._bbox,
                            confidence=table.parsing_report['accuracy'] / 100.0,
                            extraction_method="camelot_lattice",
                            metadata={
                                'whitespace': table.parsing_report['whitespace'],
                                'order': table.parsing_report['order']
                            }
                        )
                        tables.append(table_data)
                
                logging.info(f"Extracted {len(tables)} tables with Camelot lattice mode")
                
            except Exception as e:
                logging.warning(f"Camelot lattice mode failed: {e}")
            
            # Stream mode (для таблиц без линий)
            try:
                stream_tables = camelot.read_pdf(
                    pdf_path, 
                    pages='all', 
                    flavor='stream',
                    suppress_stdout=True
                )
                
                for table in stream_tables:
                    if table.parsing_report['accuracy'] > 80:
                        table_data = TableData(
                            data=table.df.values.tolist(),
                            rows=len(table.df),
                            cols=len(table.df.columns),
                            page=table.page,
                            bbox=table._bbox,
                            confidence=table.parsing_report['accuracy'] / 100.0,
                            extraction_method="camelot_stream",
                            metadata={
                                'whitespace': table.parsing_report['whitespace'],
                                'order': table.parsing_report['order']
                            }
                        )
                        tables.append(table_data)
                
                logging.info(f"Extracted {len(stream_tables)} tables with Camelot stream mode")
                
            except Exception as e:
                logging.warning(f"Camelot stream mode failed: {e}")
            
            success_rate = len(tables) / max(len(methods_used), 1)
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                extraction_methods_used=methods_used,
                success_rate=success_rate
            )
            
        except Exception as e:
            logging.error(f"Error with Camelot extraction: {e}")
            raise
    
    def _extract_with_tabula(self, pdf_path: str) -> TableExtractionResult:
        """Извлечение таблиц с помощью Tabula"""
        if not self.tabula_available:
            raise ImportError("Tabula not available")
        
        try:
            tables = []
            methods_used = ["tabula"]
            
            # Получаем все таблицы из PDF
            all_tables = tabula.read_pdf(
                pdf_path,
                pages='all',
                multiple_tables=True,
                guess=False,
                stream=True
            )
            
            for i, table in enumerate(all_tables):
                if not table.empty:
                    # Преобразуем DataFrame в список
                    table_data = TableData(
                        data=table.values.tolist(),
                        rows=len(table),
                        cols=len(table.columns),
                        page=i + 1,  # Tabula не дает номер страницы
                        confidence=0.7,  # Примерная оценка для Tabula
                        extraction_method="tabula",
                        metadata={
                            'columns': table.columns.tolist(),
                            'index': table.index.tolist()
                        }
                    )
                    tables.append(table_data)
            
            success_rate = len(tables) / max(len(methods_used), 1)
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                extraction_methods_used=methods_used,
                success_rate=success_rate
            )
            
        except Exception as e:
            logging.error(f"Error with Tabula extraction: {e}")
            raise
    
    def _extract_with_paddle(self, pdf_path: str) -> TableExtractionResult:
        """Извлечение таблиц с помощью PaddleOCR"""
        if not self.paddle_available:
            raise ImportError("PaddleOCR not available")
        
        try:
            tables = []
            methods_used = ["paddle"]
            
            # Конвертируем PDF в изображения
            from pdf2image import convert_from_path
            
            pages = convert_from_path(pdf_path, dpi=300)
            
            for i, page in enumerate(pages):
                # Сохраняем страницу как изображение
                temp_image_path = f"/tmp/rag_page_{i+1}.png"
                page.save(temp_image_path, 'PNG')
                
                try:
                    # Извлекаем таблицы с этой страницы
                    table_data = self._extract_table_structure_paddle(temp_image_path)
                    
                    if table_data and table_data.get('structure', {}).get('type') == 'table':
                        structure = table_data['structure']
                        
                        table = TableData(
                            data=structure.get('cells', []),
                            rows=structure.get('rows', 0),
                            cols=structure.get('max_cols', 0),
                            page=i + 1,
                            confidence=0.8,
                            extraction_method="paddle",
                            metadata={
                                'orientation': table_data.get('orientation', 0)
                            }
                        )
                        tables.append(table)
                
                finally:
                    # Удаляем временный файл
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
            
            success_rate = len(tables) / max(len(methods_used), 1)
            
            return TableExtractionResult(
                tables=tables,
                total_tables=len(tables),
                extraction_methods_used=methods_used,
                success_rate=success_rate
            )
            
        except ImportError:
            logging.error("pdf2image not available for PDF to image conversion")
            raise
        except Exception as e:
            logging.error(f"Error with PaddleOCR extraction: {e}")
            raise
    
    def _extract_table_structure_paddle(self, image_path: str) -> Dict[str, Any]:
        """Извлечение структуры таблицы с помощью PaddleOCR"""
        if not self.paddle_available:
            return {}
        
        try:
            import cv2
            
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                return {}
            
            # PaddleOCR для структуры таблицы
            result = self.paddle_ocr.ocr(image, cls=True)
            
            # Анализируем результат для определения структуры таблицы
            table_structure = self._analyze_table_structure(result)
            
            return {
                'orientation': 0,  # PaddleOCR автоматически определяет
                'structure': table_structure,
                'raw_result': result
            }
            
        except Exception as e:
            logging.error(f"Error extracting table structure with PaddleOCR: {e}")
            return {}
    
    def _analyze_table_structure(self, paddle_result: List) -> Dict[str, Any]:
        """Анализ структуры таблицы из результата PaddleOCR"""
        if not paddle_result:
            return {'type': 'unknown', 'cells': []}
        
        try:
            # Извлекаем все текстовые блоки
            text_blocks = []
            for line in paddle_result:
                if line:
                    for word_info in line:
                        if word_info:
                            bbox, (text, confidence) = word_info
                            text_blocks.append({
                                'text': text,
                                'confidence': confidence,
                                'bbox': bbox
                            })
            
            # Анализируем расположение для определения структуры таблицы
            if text_blocks:
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
            
            return {'type': 'unknown', 'cells': []}
            
        except Exception as e:
            logging.error(f"Error analyzing table structure: {e}")
            return {'type': 'error', 'cells': []}
    
    def get_supported_methods(self) -> List[str]:
        """Получение списка поддерживаемых методов извлечения"""
        methods = []
        
        if self.camelot_available:
            methods.append("camelot")
        if self.tabula_available:
            methods.append("tabula")
        if self.paddle_available:
            methods.append("paddle")
        
        return methods
    
    def is_available(self) -> bool:
        """Проверка доступности экстрактора таблиц"""
        return any([self.camelot_available, self.tabula_available, self.paddle_available])
