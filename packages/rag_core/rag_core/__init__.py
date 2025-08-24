"""
RAG Core - Основная логика для RAG-платформы

Этот пакет содержит:
- Парсинг документов (PDF, DOCX, XLSX, HTML, EML)
- OCR обработку с Tesseract и PaddleOCR
- Извлечение таблиц с Camelot, Tabula, PaddleOCR
- Векторное хранилище на PostgreSQL + pgvector
- Сервис эмбеддингов через Ollama
"""

__version__ = "0.1.0"
__author__ = "RAG Platform Team"

# Основные компоненты
from .parsers.document_parser import DocumentParser, DocumentContent, DocumentChunk
from .ocr.ocr_processor import OCRProcessor, OCRResult, ImagePage
from .tables.table_extractor import TableExtractor, TableData, TableExtractionResult
from .vectorstore.pgvector_store import PgVectorStore, SearchResult
from .embeddings.embedding_service import (
    OllamaEmbeddingService, 
    MockEmbeddingService, 
    EmbeddingResult,
    create_embedding_service,
    normalize_embedding,
    cosine_similarity,
    euclidean_distance
)

# Основные классы для импорта
__all__ = [
    # Парсеры
    "DocumentParser",
    "DocumentContent", 
    "DocumentChunk",
    
    # OCR
    "OCRProcessor",
    "OCRResult",
    "ImagePage",
    
    # Таблицы
    "TableExtractor",
    "TableData",
    "TableExtractionResult",
    
    # Векторное хранилище
    "PgVectorStore",
    "SearchResult",
    
    # Эмбеддинги
    "OllamaEmbeddingService",
    "MockEmbeddingService", 
    "EmbeddingResult",
    "create_embedding_service",
    
    # Утилиты
    "normalize_embedding",
    "cosine_similarity",
    "euclidean_distance",
]

# Версия
__version_info__ = tuple(int(x) for x in __version__.split('.'))
