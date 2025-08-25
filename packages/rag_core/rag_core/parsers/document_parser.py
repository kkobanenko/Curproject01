"""
Парсер документов для RAG-платформы
Поддерживает PDF, DOCX, XLSX, HTML, EML форматы
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional
import mimetypes

logger = logging.getLogger(__name__)

class DocumentParser(ABC):
    """Базовый класс для парсинга документов различных форматов"""
    
    def __init__(self):
        self.supported_mime_types: List[str] = []
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Проверяет, может ли парсер обработать данный файл"""
        pass
    
    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсит документ и возвращает структурированные данные"""
        pass
    
    def get_mime_type(self, file_path: Path) -> Optional[str]:
        """Определяет MIME-тип файла"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type

class DocumentParserRegistry:
    """Реестр парсеров документов"""
    
    def __init__(self):
        self._parsers: List[DocumentParser] = []
    
    def register(self, parser: DocumentParser):
        """Регистрирует новый парсер"""
        self._parsers.append(parser)
        logger.info(f"Registered parser: {parser.__class__.__name__}")
    
    def get_parser(self, file_path: Path) -> Optional[DocumentParser]:
        """Находит подходящий парсер для файла"""
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        return None
    
    def get_supported_extensions(self) -> List[str]:
        """Возвращает список поддерживаемых расширений файлов"""
        extensions = set()
        for parser in self._parsers:
            for mime_type in parser.supported_mime_types:
                ext = mimetypes.guess_extension(mime_type)
                if ext:
                    extensions.add(ext)
        return list(extensions)
