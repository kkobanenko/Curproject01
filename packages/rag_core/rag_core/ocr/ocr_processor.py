"""
OCR процессор для RAG-платформы
Поддерживает Tesseract с автоматическим определением ориентации
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import cv2
import numpy as np

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available, OCR disabled")

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logging.warning("PaddleOCR not available, table structure detection disabled")

@dataclass
class OCRResult:
    """Результат OCR обработки"""
    text: str
    confidence: float
    orientation: int
    bbox: Optional[Dict[str, Any]] = None
    language: str = 'rus+eng'

@dataclass
class ImagePage:
    """Страница изображения"""
    image: np.ndarray
    page_num: int
    original_orientation: int
    detected_orientation: int
    text: str
    confidence: float

class OCRProcessor:
    """Основной OCR процессор"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.paddle_available = PADDLE_AVAILABLE
        
        if self.tesseract_available:
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Проверяем доступность Tesseract
            try:
                pytesseract.get_tesseract_version()
                logging.info("Tesseract OCR initialized successfully")
            except Exception as e:
                logging.warning(f"Tesseract OCR not available: {e}")
                self.tesseract_available = False
        
        if self.paddle_available:
            try:
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
                logging.info("PaddleOCR initialized successfully")
            except Exception as e:
                logging.warning(f"PaddleOCR not available: {e}")
                self.paddle_available = False
    
    def process(self, content: Any) -> Any:
        """Обработка контента с OCR"""
        # Здесь будет логика обработки DocumentContent
        # Пока заглушка
        return content
    
    def process_image(self, image_path: str, languages: str = 'rus+eng') -> OCRResult:
        """OCR обработка изображения с автоматическим определением ориентации"""
        if not self.tesseract_available:
            raise ImportError("Tesseract OCR not available")
        
        try:
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Определяем ориентацию
            orientation = self._detect_orientation(image, languages)
            
            # Поворачиваем изображение если нужно
            if orientation != 0:
                image = self._rotate_image(image, orientation)
            
            # Выполняем OCR
            text = pytesseract.image_to_string(
                image, 
                lang=languages,
                config='--psm 6'  # Page segmentation mode: uniform block of text
            )
            
            # Получаем confidence score
            confidence = self._get_confidence(image, languages)
            
            return OCRResult(
                text=text.strip(),
                confidence=confidence,
                orientation=orientation,
                language=languages
            )
            
        except Exception as e:
            logging.error(f"Error processing image {image_path}: {e}")
            raise
    
    def process_pdf_pages(self, pdf_path: str, output_dir: str, languages: str = 'rus+eng') -> List[OCRResult]:
        """OCR обработка страниц PDF"""
        if not self.tesseract_available:
            raise ImportError("Tesseract OCR not available")
        
        try:
            from pdf2image import convert_from_path
            
            # Конвертируем PDF в изображения
            pages = convert_from_path(pdf_path, dpi=300)
            results = []
            
            os.makedirs(output_dir, exist_ok=True)
            
            for i, page in enumerate(pages):
                # Сохраняем страницу как изображение
                page_path = os.path.join(output_dir, f"page_{i+1}.png")
                page.save(page_path, 'PNG')
                
                # Обрабатываем OCR
                result = self.process_image(page_path, languages)
                result.bbox = {'page': i + 1}
                
                results.append(result)
                
                # Удаляем временный файл
                os.remove(page_path)
            
            return results
            
        except ImportError:
            logging.error("pdf2image not available for PDF OCR processing")
            raise
        except Exception as e:
            logging.error(f"Error processing PDF {pdf_path}: {e}")
            raise
    
    def extract_table_structure(self, image_path: str) -> Dict[str, Any]:
        """Извлечение структуры таблицы с помощью PaddleOCR"""
        if not self.paddle_available:
            raise ImportError("PaddleOCR not available")
        
        try:
            # Загружаем изображение
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Определяем ориентацию
            orientation = self._detect_orientation(image)
            if orientation != 0:
                image = self._rotate_image(image, orientation)
            
            # PaddleOCR для структуры таблицы
            result = self.paddle_ocr.ocr(image, cls=True)
            
            # Анализируем результат для определения структуры таблицы
            table_structure = self._analyze_table_structure(result)
            
            return {
                'orientation': orientation,
                'structure': table_structure,
                'raw_result': result
            }
            
        except Exception as e:
            logging.error(f"Error extracting table structure from {image_path}: {e}")
            raise
    
    def _detect_orientation(self, image: np.ndarray, languages: str = 'rus+eng') -> int:
        """Автоматическое определение ориентации изображения"""
        if not self.tesseract_available:
            return 0
        
        try:
            # Пробуем разные ориентации
            orientations = [0, 90, 180, 270]
            best_orientation = 0
            best_confidence = 0
            
            for angle in orientations:
                if angle == 0:
                    rotated_image = image
                else:
                    rotated_image = self._rotate_image(image, angle)
                
                # Получаем confidence для текущей ориентации
                confidence = self._get_confidence(rotated_image, languages)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_orientation = angle
            
            logging.info(f"Detected orientation: {best_orientation}° (confidence: {best_confidence:.2f})")
            return best_orientation
            
        except Exception as e:
            logging.warning(f"Could not detect orientation: {e}")
            return 0
    
    def _rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Поворот изображения на заданный угол"""
        if angle == 0:
            return image
        
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # Создаем матрицу поворота
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Вычисляем новые размеры
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        
        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))
        
        # Корректируем матрицу поворота
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # Применяем поворот
        rotated_image = cv2.warpAffine(image, rotation_matrix, (new_width, new_height))
        
        return rotated_image
    
    def _get_confidence(self, image: np.ndarray, languages: str = 'rus+eng') -> float:
        """Получение confidence score для изображения"""
        if not self.tesseract_available:
            return 0.0
        
        try:
            # Получаем данные с confidence
            data = pytesseract.image_to_data(
                image, 
                lang=languages,
                output_type=pytesseract.Output.DICT,
                config='--psm 6'
            )
            
            # Вычисляем средний confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            
            if confidences:
                return sum(confidences) / len(confidences) / 100.0  # Нормализуем к 0-1
            else:
                return 0.0
                
        except Exception as e:
            logging.warning(f"Could not get confidence: {e}")
            return 0.0
    
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
    
    def get_supported_languages(self) -> List[str]:
        """Получение списка поддерживаемых языков"""
        if not self.tesseract_available:
            return []
        
        try:
            # Получаем список доступных языков
            languages = pytesseract.get_languages()
            return languages
        except Exception as e:
            logging.warning(f"Could not get supported languages: {e}")
            return ['eng']  # Fallback к английскому
    
    def is_available(self) -> bool:
        """Проверка доступности OCR"""
        return self.tesseract_available or self.paddle_available
