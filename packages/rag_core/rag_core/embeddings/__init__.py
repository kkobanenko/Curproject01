"""
Сервис эмбеддингов для RAG-платформы
"""

from .embedding_service import (
    OllamaEmbeddingService,
    MockEmbeddingService,
    EmbeddingResult,
    create_embedding_service,
    normalize_embedding,
    cosine_similarity,
    euclidean_distance
)

__all__ = [
    "OllamaEmbeddingService",
    "MockEmbeddingService", 
    "EmbeddingResult",
    "create_embedding_service",
    "normalize_embedding",
    "cosine_similarity",
    "euclidean_distance"
]
