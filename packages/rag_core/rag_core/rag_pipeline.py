from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio

from .parsers.document_parser import DocumentParserRegistry
from .parsers.pdf_parser import PDFParser
from .parsers.docx_parser import DOCXParser
from .chunking.chunker import DocumentChunker, Chunk
from .embeddings.embedding_service import EmbeddingService
from .vectorstore.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Основной класс RAG pipeline"""
    
    def __init__(self, 
                 vector_store: PgVectorStore,
                 embedding_service: EmbeddingService,
                 chunk_size: int = 1000,
                 overlap: int = 200):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Инициализируем парсеры
        self.parser_registry = DocumentParserRegistry()
        self._register_parsers()
        
        # Инициализируем чанкер
        self.chunker = DocumentChunker(
            strategy='mixed',
            chunk_size=chunk_size,
            overlap=overlap
        )
    
    def _register_parsers(self):
        """Регистрирует доступные парсеры"""
        try:
            self.parser_registry.register(PDFParser())
            logger.info("PDF parser registered")
        except Exception as e:
            logger.warning(f"Failed to register PDF parser: {e}")
        
        try:
            self.parser_registry.register(DOCXParser())
            logger.info("DOCX parser registered")
        except Exception as e:
            logger.warning(f"Failed to register DOCX parser: {e}")
    
    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """Обрабатывает документ полностью: парсинг -> чанкинг -> эмбеддинги -> сохранение"""
        try:
            logger.info(f"Processing document: {file_path}")
            
            # 1. Парсинг документа
            parsed_content = await self._parse_document(file_path)
            if not parsed_content:
                raise ValueError(f"Failed to parse document: {file_path}")
            
            # 2. Чанкинг
            chunks = await self._chunk_document(parsed_content)
            if not chunks:
                logger.warning(f"No chunks created for document: {file_path}")
                return {"error": "No chunks created"}
            
            # 3. Генерация эмбеддингов
            embeddings = await self._generate_embeddings(chunks)
            if not embeddings:
                raise ValueError("Failed to generate embeddings")
            
            # 4. Сохранение в векторное хранилище
            doc_id = await self._save_to_vectorstore(file_path, parsed_content, chunks, embeddings)
            
            # 5. Статистика
            stats = self._get_processing_stats(parsed_content, chunks, embeddings)
            
            logger.info(f"Document processed successfully: {file_path} -> {len(chunks)} chunks")
            
            return {
                "success": True,
                "document_id": doc_id,
                "chunks_count": len(chunks),
                "embeddings_count": len(embeddings),
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": str(file_path)
            }
    
    async def _parse_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Парсит документ"""
        try:
            parser = self.parser_registry.get_parser(file_path)
            if not parser:
                logger.error(f"No parser available for file: {file_path}")
                return None
            
            # Выполняем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            parsed_content = await loop.run_in_executor(None, parser.parse, file_path)
            
            return parsed_content
            
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {e}")
            return None
    
    async def _chunk_document(self, parsed_content: Dict[str, Any]) -> List[Chunk]:
        """Разбивает документ на чанки"""
        try:
            # Выполняем чанкинг в отдельном потоке
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None, 
                self.chunker.chunk_document, 
                parsed_content
            )
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return []
    
    async def _generate_embeddings(self, chunks: List[Chunk]) -> List[List[float]]:
        """Генерирует эмбеддинги для чанков"""
        try:
            texts = [chunk.text for chunk in chunks]
            
            # Генерируем эмбеддинги батчами
            embeddings = await self.embedding_service.get_embeddings_batch_async(texts)
            
            # Проверяем валидность
            valid_embeddings = []
            for i, embedding in enumerate(embeddings):
                if self.embedding_service.validate_embedding(embedding):
                    valid_embeddings.append(embedding)
                else:
                    logger.warning(f"Invalid embedding for chunk {i}")
                    # Создаем нулевой вектор
                    valid_embeddings.append([0.0] * self.embedding_service.get_embedding_dimension())
            
            return valid_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
    
    async def _save_to_vectorstore(self, 
                                  file_path: Path, 
                                  parsed_content: Dict[str, Any],
                                  chunks: List[Chunk],
                                  embeddings: List[List[float]]) -> str:
        """Сохраняет документ в векторное хранилище"""
        try:
            # Создаем или обновляем документ
            doc_id = self.vector_store.ensure_document(
                path=str(file_path),
                sha256=parsed_content.get('sha256', ''),
                title=parsed_content.get('title', file_path.name)
            )
            
            # Подготавливаем данные для сохранения
            payloads = []
            for chunk in chunks:
                payload = {
                    'idx': chunk.chunk_index,
                    'kind': chunk.chunk_type,
                    'text': chunk.text,
                    'table_html': chunk.table_html,
                    'bbox': chunk.bbox,
                    'page_no': chunk.page_no
                }
                payloads.append(payload)
            
            # Сохраняем чанки и эмбеддинги
            self.vector_store.upsert_chunks_and_embeddings(doc_id, payloads, embeddings)
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error saving to vectorstore: {e}")
            raise
    
    def _get_processing_stats(self, 
                             parsed_content: Dict[str, Any],
                             chunks: List[Chunk],
                             embeddings: List[List[float]]) -> Dict[str, Any]:
        """Возвращает статистику обработки"""
        chunk_stats = self.chunker.get_chunk_statistics(chunks)
        
        return {
            'document': {
                'title': parsed_content.get('title', 'Unknown'),
                'mime_type': parsed_content.get('mime_type', 'Unknown'),
                'needs_ocr': parsed_content.get('needs_ocr', False),
                'page_count': parsed_content.get('page_count', 0),
                'has_tables': parsed_content.get('has_tables', False)
            },
            'chunks': chunk_stats,
            'embeddings': {
                'count': len(embeddings),
                'dimension': self.embedding_service.get_embedding_dimension(),
                'model': self.embedding_service.model_name
            }
        }
    
    async def search(self, 
                    query: str, 
                    top_k: int = 20,
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Выполняет семантический поиск"""
        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = await self.embedding_service.get_embedding_async(query)
            
            # Ищем в векторном хранилище
            results = self.vector_store.search(query_embedding, top_k)
            
            # Применяем фильтры если есть
            if filters:
                results = self._apply_filters(results, filters)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Применяет фильтры к результатам поиска"""
        filtered_results = []
        
        for result in results:
            # Проверяем соответствие фильтрам
            if self._matches_filters(result, filters):
                filtered_results.append(result)
        
        return filtered_results
    
    def _matches_filters(self, result: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Проверяет, соответствует ли результат фильтрам"""
        for key, value in filters.items():
            if key in result:
                if isinstance(value, list):
                    if result[key] not in value:
                        return False
                elif result[key] != value:
                    return False
        
        return True
    
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Получает чанки документа по ID"""
        try:
            # Здесь можно добавить метод для получения чанков документа
            # пока возвращаем пустой список
            return []
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
    
    def get_supported_formats(self) -> List[str]:
        """Возвращает поддерживаемые форматы файлов"""
        return self.parser_registry.get_supported_extensions()
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Возвращает информацию о pipeline"""
        return {
            'chunk_size': self.chunk_size,
            'overlap': self.overlap,
            'embedding_model': self.embedding_service.model_name,
            'embedding_dimension': self.embedding_service.get_embedding_dimension(),
            'supported_formats': self.get_supported_formats(),
            'vector_store_type': 'pgvector',
            'chunking_strategy': 'mixed'
        }
