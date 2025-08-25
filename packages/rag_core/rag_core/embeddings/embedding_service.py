"""
Сервис эмбеддингов для RAG-платформы
Поддерживает Ollama для локальной генерации векторов
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Union
import asyncio
import json
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Сервис для работы с эмбеддингами"""
    
    def __init__(self, 
                 model_name: str = "bge-m3",
                 base_url: str = "http://localhost:11434",
                 embedding_dim: int = 1024,
                 batch_size: int = 32):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Проверяет подключение к Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [model['name'] for model in models]
                logger.info(f"Available Ollama models: {available_models}")
                
                if self.model_name not in available_models:
                    logger.warning(f"Model {self.model_name} not found in Ollama. Available: {available_models}")
            else:
                logger.error(f"Failed to connect to Ollama: {response.status_code}")
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Получает эмбеддинг для одного текста"""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                embedding = result.get('embedding', [])
                
                if len(embedding) != self.embedding_dim:
                    logger.warning(f"Expected embedding dimension {self.embedding_dim}, got {len(embedding)}")
                
                return embedding
            else:
                logger.error(f"Failed to get embedding: {response.status_code} - {response.text}")
                raise Exception(f"Embedding API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Получает эмбеддинги для батча текстов"""
        embeddings = []
        
        # Обрабатываем батчами для избежания перегрузки
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            logger.debug(f"Processing batch {i//self.batch_size + 1}: {len(batch)} texts")
            
            batch_embeddings = []
            for text in batch:
                try:
                    embedding = self.get_embedding(text)
                    batch_embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Error getting embedding for text: {e}")
                    # Возвращаем нулевой вектор в случае ошибки
                    batch_embeddings.append([0.0] * self.embedding_dim)
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def get_embedding_async(self, text: str) -> List[float]:
        """Асинхронно получает эмбеддинг для одного текста"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_embedding, text)
    
    async def get_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Асинхронно получает эмбеддинги для батча текстов"""
        tasks = [self.get_embedding_async(text) for text in texts]
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем ошибки
        processed_embeddings = []
        for i, embedding in enumerate(embeddings):
            if isinstance(embedding, Exception):
                logger.error(f"Error getting embedding for text {i}: {embedding}")
                processed_embeddings.append([0.0] * self.embedding_dim)
            else:
                processed_embeddings.append(embedding)
        
        return processed_embeddings
    
    def get_embedding_dimension(self) -> int:
        """Возвращает размерность эмбеддингов"""
        return self.embedding_dim
    
    def is_model_available(self) -> bool:
        """Проверяет доступность модели"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [model['name'] for model in models]
                return self.model_name in available_models
            return False
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получает информацию о модели"""
        try:
            response = requests.get(f"{self.base_url}/api/show", 
                                 json={"name": self.model_name}, 
                                 timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get model info: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Error getting model info: {e}"}
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Вычисляет косинусное сходство между двумя эмбеддингами"""
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        # Нормализуем векторы
        norm1 = sum(x * x for x in embedding1) ** 0.5
        norm2 = sum(x * x for x in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Вычисляем косинусное сходство
        dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
        similarity = dot_product / (norm1 * norm2)
        
        return similarity
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         top_k: int = 5) -> List[Dict[str, Any]]:
        """Находит наиболее похожие эмбеддинги"""
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            try:
                similarity = self.calculate_similarity(query_embedding, candidate)
                similarities.append({
                    'index': i,
                    'similarity': similarity,
                    'embedding': candidate
                })
            except Exception as e:
                logger.warning(f"Error calculating similarity for embedding {i}: {e}")
                continue
        
        # Сортируем по убыванию сходства
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Возвращаем top_k результатов
        return similarities[:top_k]
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Проверяет валидность эмбеддинга"""
        if not isinstance(embedding, list):
            return False
        
        if len(embedding) != self.embedding_dim:
            return False
        
        # Проверяем, что все элементы - числа
        try:
            return all(isinstance(x, (int, float)) for x in embedding)
        except Exception:
            return False

class LocalEmbeddingService(EmbeddingService):
    """Локальный сервис эмбеддингов (для случаев без Ollama)"""
    
    def __init__(self, model_path: Optional[Path] = None, embedding_dim: int = 1024):
        super().__init__(embedding_dim=embedding_dim)
        self.model_path = model_path
        self._load_local_model()
    
    def _load_local_model(self):
        """Загружает локальную модель"""
        # Здесь можно добавить загрузку локальных моделей
        # например, через sentence-transformers или ONNX
        logger.info("Local embedding service initialized")
    
    def get_embedding(self, text: str) -> List[float]:
        """Получает эмбеддинг используя локальную модель"""
        # Заглушка - возвращает случайный вектор
        # В реальной реализации здесь будет загрузка локальной модели
        import random
        random.seed(hash(text) % 2**32)
        return [random.uniform(-1, 1) for _ in range(self.embedding_dim)]
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Получает эмбеддинги для батча текстов"""
        return [self.get_embedding(text) for text in texts]
