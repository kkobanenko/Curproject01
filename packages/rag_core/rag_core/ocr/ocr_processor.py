"""
OCR процессор для RAG-платформы
Поддерживает Tesseract с автоматическим определением ориентации
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available, OCR processing disabled")

class OCRProcessor:
    """Процессор OCR для обработки изображений и сканов"""
    
    def __init__(self, 
                 tesseract_path: Optional[str] = None,
                 languages: List[str] = None,
                 config: str = '--oem 3 --psm 6'):
        self.tesseract_path = tesseract_path
        self.languages = languages or ['eng', 'rus']
        self.config = config
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Проверяет доступность зависимостей"""
        if not TESSERACT_AVAILABLE:
            logger.error("pytesseract not available - OCR processing will fail")
            return
        
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        # Проверяем доступность Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
    
    def process_image(self, image_path: Path) -> Dict[str, Any]:
        """Обрабатывает изображение с OCR"""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract not available")
        
        try:
            # Загружаем изображение
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Cannot load image: {image_path}")
            
            # Предобработка изображения
            processed_image = self._preprocess_image(image)
            
            # Определяем ориентацию
            orientation = self._detect_orientation(processed_image)
            
            # Поворачиваем если нужно
            if orientation != 0:
                processed_image = self._rotate_image(processed_image, orientation)
            
            # Выполняем OCR
            ocr_result = self._perform_ocr(processed_image)
            
            # Постобработка текста
            processed_text = self._postprocess_text(ocr_result['text'])
            
            return {
                'text': processed_text,
                'confidence': ocr_result['confidence'],
                'orientation': orientation,
                'image_size': image.shape[:2],
                'processed_image_size': processed_image.shape[:2],
                'ocr_config': self.config,
                'languages': self.languages
            }
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения для улучшения OCR"""
        # Конвертируем в оттенки серого
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Увеличиваем контраст
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Убираем шум
        denoised = cv2.fastNlMeansDenoising(enhanced)
        
        # Бинаризация
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _detect_orientation(self, image: np.ndarray) -> int:
        """Определяет ориентацию изображения"""
        if not TESSERACT_AVAILABLE:
            return 0
        
        try:
            # Пробуем разные углы поворота
            angles = [0, 90, 180, 270]
            best_angle = 0
            best_confidence = 0
            
            for angle in angles:
                if angle == 0:
                    rotated = image
                else:
                    rotated = self._rotate_image(image, angle)
                
                # Выполняем OCR с минимальной конфигурацией
                config = '--oem 3 --psm 1'  # Автоматическое определение страницы
                text = pytesseract.image_to_string(rotated, config=config, lang='+'.join(self.languages))
                
                # Простая оценка качества по количеству символов и слов
                confidence = len(text.strip()) + len(text.split()) * 10
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_angle = angle
            
            logger.info(f"Detected orientation: {best_angle}° (confidence: {best_confidence})")
            return best_angle
            
        except Exception as e:
            logger.warning(f"Error detecting orientation: {e}")
            return 0
    
    def _rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Поворачивает изображение на заданный угол"""
        if angle == 0:
            return image
        
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # Создаем матрицу поворота
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Выполняем поворот
        rotated = cv2.warpAffine(image, rotation_matrix, (width, height))
        
        return rotated
    
    def _perform_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Выполняет OCR на изображении"""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract not available")
        
        try:
            # Получаем текст и данные
            data = pytesseract.image_to_data(
                image, 
                config=self.config, 
                lang='+'.join(self.languages),
                output_type=pytesseract.Output.DICT
            )
            
            # Извлекаем текст
            text = pytesseract.image_to_string(
                image, 
                config=self.config, 
                lang='+'.join(self.languages)
            )
            
            # Вычисляем среднюю уверенность
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text,
                'confidence': avg_confidence,
                'raw_data': data
            }
            
        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
            raise
    
    def _postprocess_text(self, text: str) -> str:
        """Постобработка распознанного текста"""
        if not text:
            return ""
        
        # Убираем лишние пробелы
        text = ' '.join(text.split())
        
        # Исправляем типичные ошибки OCR
        text = text.replace('|', 'I')  # Частая ошибка
        text = text.replace('0', 'O')  # В некоторых шрифтах
        text = text.replace('1', 'l')  # В некоторых шрифтах
        
        # Убираем одиночные символы в начале строк
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 1:  # Пропускаем строки с одним символом
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def process_pdf_page(self, pdf_path: Path, page_number: int) -> Dict[str, Any]:
        """Обрабатывает страницу PDF с OCR"""
        try:
            # Конвертируем страницу PDF в изображение
            image = self._pdf_page_to_image(pdf_path, page_number)
            
            # Обрабатываем изображение
            return self._process_cv_image(image)
            
        except Exception as e:
            logger.error(f"Error processing PDF page {page_number} from {pdf_path}: {e}")
            raise
    
    def _pdf_page_to_image(self, pdf_path: Path, page_number: int) -> np.ndarray:
        """Конвертирует страницу PDF в изображение"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(str(pdf_path))
            page = doc[page_number]
            
            # Рендерим страницу в изображение
            mat = fitz.Matrix(2.0, 2.0)  # Увеличиваем разрешение
            pix = page.get_pixmap(matrix=mat)
            
            # Конвертируем в numpy array
            img_data = pix.tobytes("png")
            nparr = np.frombuffer(img_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            doc.close()
            return image
            
        except ImportError:
            logger.warning("PyMuPDF not available, using alternative method")
            # Альтернативный метод с pdf2image
            try:
                from pdf2image import convert_from_path
                
                images = convert_from_path(str(pdf_path), first_page=page_number+1, last_page=page_number+1)
                if images:
                    # Конвертируем PIL в OpenCV
                    pil_image = images[0]
                    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    return opencv_image
                else:
                    raise ValueError(f"Cannot convert PDF page {page_number}")
                    
            except ImportError:
                raise RuntimeError("Neither PyMuPDF nor pdf2image available for PDF processing")
    
    def _process_cv_image(self, image: np.ndarray) -> Dict[str, Any]:
        """Обрабатывает OpenCV изображение"""
        # Предобработка
        processed_image = self._preprocess_image(image)
        
        # Определяем ориентацию
        orientation = self._detect_orientation(processed_image)
        
        # Поворачиваем если нужно
        if orientation != 0:
            processed_image = self._rotate_image(processed_image, orientation)
        
        # Выполняем OCR
        ocr_result = self._perform_ocr(processed_image)
        
        # Постобработка текста
        processed_text = self._postprocess_text(ocr_result['text'])
        
        return {
            'text': processed_text,
            'confidence': ocr_result['confidence'],
            'orientation': orientation,
            'image_size': image.shape[:2],
            'processed_image_size': processed_image.shape[:2]
        }
    
    def get_supported_languages(self) -> List[str]:
        """Возвращает поддерживаемые языки"""
        if not TESSERACT_AVAILABLE:
            return []
        
        try:
            languages = pytesseract.get_languages()
            return languages
        except Exception:
            return ['eng']  # Fallback
    
    def is_available(self) -> bool:
        """Проверяет доступность OCR"""
        return TESSERACT_AVAILABLE and self._check_tesseract_installation()
    
    def _check_tesseract_installation(self) -> bool:
        """Проверяет установку Tesseract"""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
