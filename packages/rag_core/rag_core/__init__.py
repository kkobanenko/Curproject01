"""
RAG Core - Core RAG functionality for document processing, embeddings, and vector search.

This package provides:
- Document parsing for various formats (PDF, DOCX, XLSX, HTML, etc.)
- Table extraction using advanced algorithms
- OCR processing for scanned documents
- Smart document chunking strategies
- Embedding generation and vector search
- PostgreSQL + pgvector integration
"""

from .parsers.document_parser import DocumentParser, DocumentParserRegistry
from .parsers.pdf_parser import PDFParser
from .parsers.docx_parser import DOCXParser
from .chunking.chunker import DocumentChunker, Chunk
from .embeddings.embedding_service import EmbeddingService
from .vectorstore.pgvector_store import PgVectorStore
from .rag_pipeline import RAGPipeline

__version__ = "0.1.0"
__author__ = "RAG Platform Team"

__all__ = [
    # Core classes
    "DocumentParser",
    "DocumentParserRegistry",
    "DocumentChunker",
    "Chunk",
    "EmbeddingService",
    "PgVectorStore",
    "RAGPipeline",
    
    # Parser implementations
    "PDFParser",
    "DOCXParser",
]
