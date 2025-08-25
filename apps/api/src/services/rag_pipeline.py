"""
RAG пайплайн для генерации ответов
"""
import logging
import time
from typing import List, Dict, Any, Optional
import httpx
from .embeddings import EmbeddingService
from .vectorstore import VectorStoreService
from ..settings import get_settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG пайплайн: Retrieve -> (Rerank) -> Generate"""
    
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self._ollama_client: Optional[httpx.AsyncClient] = None
    
    async def _get_ollama_client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент для Ollama"""
        if self._ollama_client is None:
            self._ollama_client = httpx.AsyncClient(timeout=60.0)
        return self._ollama_client
    
    async def close(self):
        """Закрыть клиенты"""
        await self.embedding_service.close()
        await self.vector_store.close()
        if self._ollama_client:
            await self._ollama_client.aclose()
            self._ollama_client = None
    
    async def generate_answer(
        self,
        query: str,
        top_k: int = 5,
        use_rerank: bool = False,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Генерировать ответ на основе RAG пайплайна"""
        start_time = time.time()
        
        try:
            # 1. Генерируем эмбеддинг для запроса
            query_embedding = await self.embedding_service.generate_embedding(query)
            if not query_embedding:
                return {
                    "error": "Failed to generate query embedding",
                    "message": "Не удалось обработать запрос"
                }
            
            # 2. Ищем релевантные документы
            search_results = await self.vector_store.search_similar(
                query_embedding,
                top_k=top_k,
                tenant_id=tenant_id
            )
            
            if not search_results:
                return {
                    "error": "No relevant documents found",
                    "message": "Не найдено релевантных документов"
                }
            
            # 3. (Опционально) Переранжирование
            if use_rerank and len(search_results) > self.settings.top_rerank:
                search_results = await self._rerank_results(query, search_results)
                search_results = search_results[:self.settings.top_rerank]
            
            # 4. Формируем контекст
            context = self._build_context(search_results)
            
            # 5. Генерируем ответ через LLM
            answer = await self._generate_llm_response(query, context)
            
            # 6. Формируем цитаты
            citations = self._build_citations(search_results)
            
            processing_time = time.time() - start_time
            
            return {
                "message": answer,
                "citations": citations,
                "processing_time": processing_time,
                "context_length": len(context),
                "documents_used": len(set(r["doc_id"] for r in search_results))
            }
            
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            return {
                "error": "Pipeline error",
                "message": f"Ошибка обработки: {str(e)}"
            }
    
    async def _rerank_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Переранжирование результатов поиска"""
        try:
            # Простая реализация: используем cross-encoder через Ollama
            # В будущем можно подключить специализированный reranker
            client = await self._get_ollama_client()
            
            # Формируем промпт для переранжирования
            rerank_prompt = f"""
            Запрос: {query}
            
            Документы (ранжируйте по релевантности, где 1 - самый релевантный):
            """
            
            for i, result in enumerate(results):
                content = result.get("content", "")[:200]  # Первые 200 символов
                rerank_prompt += f"\n{i+1}. {content}"
            
            rerank_prompt += "\n\nОтветьте только номерами документов в порядке релевантности:"
            
            # Генерируем ответ
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_llm_model,
                    "prompt": rerank_prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                # Парсим ответ и переранжируем
                # Это упрощенная реализация
                return results  # Пока возвращаем как есть
            
            return results
            
        except Exception as e:
            logger.warning(f"Reranking failed: {e}")
            return results
    
    def _build_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Формирование контекста из результатов поиска"""
        context_parts = []
        
        for i, result in enumerate(search_results):
            kind = result.get("kind", "text")
            content = result.get("content", "")
            table_html = result.get("table_html", "")
            page_no = result.get("page_no", "")
            
            if kind == "table" and table_html:
                context_parts.append(f"Таблица (стр. {page_no}): {table_html}")
            elif content:
                context_parts.append(f"Текст (стр. {page_no}): {content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_llm_response(self, query: str, context: str) -> str:
        """Генерация ответа через LLM"""
        try:
            client = await self._get_ollama_client()
            
            prompt = f"""
            Контекст:
            {context}
            
            Вопрос: {query}
            
            Ответь на вопрос, используя только предоставленный контекст. 
            Если в контексте нет информации для ответа, скажи об этом.
            """
            
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_llm_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Не удалось сгенерировать ответ")
            else:
                return "Ошибка генерации ответа"
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"Ошибка генерации ответа: {str(e)}"
    
    def _build_citations(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Формирование цитат из результатов поиска"""
        citations = []
        
        for result in search_results:
            citation = {
                "doc_id": result.get("doc_id"),
                "chunk_id": result.get("id"),
                "content": result.get("content", "")[:200] + "..." if result.get("content") else "",
                "page_no": result.get("page_no"),
                "score": result.get("score", 0.0),
                "kind": result.get("kind", "text")
            }
            
            if result.get("bbox"):
                citation["bbox"] = result["bbox"]
            
            citations.append(citation)
        
        return citations
    
    async def search_documents(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Поиск документов по запросу"""
        start_time = time.time()
        
        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = await self.embedding_service.generate_embedding(query)
            if not query_embedding:
                return {
                    "error": "Failed to generate query embedding",
                    "results": [],
                    "total": 0
                }
            
            # Ищем похожие документы
            results = await self.vector_store.search_similar(
                query_embedding,
                top_k=top_k,
                filters=filters,
                tenant_id=tenant_id
            )
            
            processing_time = time.time() - start_time
            
            return {
                "query": query,
                "results": results,
                "total": len(results),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "error": "Search error",
                "results": [],
                "total": 0
            }
