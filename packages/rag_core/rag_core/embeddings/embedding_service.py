"""
Сервис эмбеддингов для RAG-платформы
Поддерживает Ollama для локальной генерации векторов
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
import json

@dataclass
class EmbeddingResult:
    """Результат генерации эмбеддинга"""
    embedding: List[float]
    model: str
    usage: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class OllamaEmbeddingService:
    """Сервис эмбеддингов через Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "bge-m3"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Проверяем доступность Ollama
        self._check_ollama_health()
    
    def _check_ollama_health(self):
        """Проверка доступности Ollama"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [model['name'] for model in models]
                
                if self.model not in available_models:
                    logging.warning(f"Model {self.model} not found in Ollama. Available: {available_models}")
                    # Пробуем использовать первую доступную модель
                    if available_models:
                        self.model = available_models[0]
                        logging.info(f"Using available model: {self.model}")
                else:
                    logging.info(f"Ollama model {self.model} is available")
            else:
                logging.warning(f"Ollama health check failed: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Error checking Ollama health: {e}")
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}")
    
    def generate_embedding(self, text: str) -> EmbeddingResult:
        """Генерация эмбеддинга для одного текста"""
        try:
            payload = {
                "model": self.model,
                "prompt": text,
                "options": {
                    "num_predict": 1,
                    "temperature": 0.0,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                return EmbeddingResult(
                    embedding=result.get('embedding', []),
                    model=self.model,
                    usage={
                        'prompt_tokens': len(text.split()),
                        'total_tokens': len(text.split()),
                        'model': self.model
                    },
                    metadata={
                        'ollama_response': result
                    }
                )
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logging.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[EmbeddingResult]:
        """Генерация эмбеддингов для списка текстов"""
        results = []
        
        # Обрабатываем батчами для избежания перегрузки
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = []
            
            for text in batch:
                try:
                    result = self.generate_embedding(text)
                    batch_results.append(result)
                except Exception as e:
                    logging.error(f"Error generating embedding for text: {e}")
                    # Создаем пустой эмбеддинг в случае ошибки
                    empty_embedding = [0.0] * 1024  # BGE-M3 размер
                    batch_results.append(EmbeddingResult(
                        embedding=empty_embedding,
                        model=self.model,
                        usage={'error': str(e)},
                        metadata={'error': True}
                    ))
            
            results.extend(batch_results)
            
            # Небольшая пауза между батчами
            if i + batch_size < len(texts):
                import time
                time.sleep(0.1)
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получение информации о модели"""
        try:
            response = self.session.get(f"{self.base_url}/api/show", params={"name": self.model})
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get model info: {response.status_code}"}
        except Exception as e:
            return {"error": f"Error getting model info: {e}"}
    
    def list_available_models(self) -> List[str]:
        """Получение списка доступных моделей"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            else:
                return []
        except Exception as e:
            logging.error(f"Error listing models: {e}")
            return []
    
    def change_model(self, new_model: str):
        """Смена модели эмбеддингов"""
        available_models = self.list_available_models()
        if new_model in available_models:
            self.model = new_model
            logging.info(f"Changed embedding model to: {new_model}")
        else:
            raise ValueError(f"Model {new_model} not available. Available: {available_models}")
    
    def is_available(self) -> bool:
        """Проверка доступности сервиса"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

class MockEmbeddingService:
    """Мок-сервис эмбеддингов для тестирования"""
    
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        import numpy as np
        self.np = np
    
    def generate_embedding(self, text: str) -> EmbeddingResult:
        """Генерация случайного эмбеддинга"""
        embedding = self.np.random.normal(0, 1, self.dimension).tolist()
        
        return EmbeddingResult(
            embedding=embedding,
            model="mock",
            usage={
                'prompt_tokens': len(text.split()),
                'total_tokens': len(text.split()),
                'model': 'mock'
            },
            metadata={'mock': True}
        )
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[EmbeddingResult]:
        """Генерация случайных эмбеддингов для списка текстов"""
        return [self.generate_embedding(text) for text in texts]
    
    def is_available(self) -> bool:
        """Всегда доступен для тестирования"""
        return True

def create_embedding_service(service_type: str = "ollama", **kwargs) -> Any:
    """Фабрика для создания сервиса эмбеддингов"""
    if service_type == "ollama":
        return OllamaEmbeddingService(**kwargs)
    elif service_type == "mock":
        return MockEmbeddingService(**kwargs)
    else:
        raise ValueError(f"Unknown embedding service type: {service_type}")

# Утилиты для работы с эмбеддингами
def normalize_embedding(embedding: List[float]) -> List[float]:
    """Нормализация вектора эмбеддинга"""
    import math
    
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude == 0:
        return embedding
    
    return [x / magnitude for x in embedding]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Вычисление косинусного сходства между векторами"""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same length")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """Вычисление евклидова расстояния между векторами"""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same length")
    
    return sum((a - b) ** 2 for a, b in zip(vec1, vec2)) ** 0.5
