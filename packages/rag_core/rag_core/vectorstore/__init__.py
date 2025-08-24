"""
Векторное хранилище для RAG-платформы
"""

from .pgvector_store import PgVectorStore, SearchResult

__all__ = ["PgVectorStore", "SearchResult"]
