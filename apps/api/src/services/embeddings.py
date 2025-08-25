"""
Сервис для работы с эмбеддингами
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
import httpx
from ..settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Сервис для работы с эмбеддингами через Ollama"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.default_model = self.settings.ollama_embed_model
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Закрыть клиент"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def is_available(self) -> bool:
        """Проверить доступность Ollama"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Получить список доступных моделей"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """Сгенерировать эмбеддинг для текста"""
        try:
            model = model or self.default_model
            client = await self._get_client()
            
            payload = {
                "model": model,
                "prompt": text
            }
            
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"Embedding generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def generate_embeddings_batch(self, texts: List[str], model: Optional[str] = None) -> List[Optional[List[float]]]:
        """Сгенерировать эмбеддинги для списка текстов"""
        model = model or self.default_model
        
        # Для Ollama делаем последовательные запросы
        # В будущем можно оптимизировать через batch API
        tasks = [self.generate_embedding(text, model) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем исключения
        embeddings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error generating embedding for text {i}: {result}")
                embeddings.append(None)
            else:
                embeddings.append(result)
        
        return embeddings
    
    async def get_model_info(self, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Получить информацию о модели"""
        try:
            model = model or self.default_model
            client = await self._get_client()
            
            response = await client.get(f"{self.base_url}/api/show", params={"name": model})
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None
