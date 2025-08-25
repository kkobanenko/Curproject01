"""
Сервис для работы с векторным хранилищем
"""
import logging
from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from ..settings import get_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Сервис для работы с PostgreSQL + pgvector"""
    
    def __init__(self):
        self.settings = get_settings()
        self.dsn = self.settings.pg_dsn
        self._connection: Optional[psycopg.Connection] = None
    
    async def _get_connection(self) -> psycopg.Connection:
        """Получить соединение с базой данных"""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.dsn)
        return self._connection
    
    async def close(self):
        """Закрыть соединение"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
    
    async def is_available(self) -> bool:
        """Проверить доступность базы данных"""
        try:
            conn = await self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.warning(f"PostgreSQL not available: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику векторного хранилища"""
        try:
            conn = await self._get_connection()
            stats = {}
            
            with conn.cursor() as cur:
                # Количество документов
                cur.execute("SELECT COUNT(*) FROM documents")
                stats["total_documents"] = cur.fetchone()[0]
                
                # Количество чанков
                cur.execute("SELECT COUNT(*) FROM chunks")
                stats["total_chunks"] = cur.fetchone()[0]
                
                # Количество эмбеддингов
                cur.execute("SELECT COUNT(*) FROM embeddings")
                stats["total_embeddings"] = cur.fetchone()[0]
                
                # Размер базы данных
                cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                stats["database_size"] = cur.fetchone()[0]
                
                # Статистика по типам чанков
                cur.execute("""
                    SELECT kind, COUNT(*) 
                    FROM chunks 
                    GROUP BY kind
                """)
                stats["chunks_by_type"] = dict(cur.fetchall())
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    async def search_similar(
        self, 
        query_vector: List[float], 
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Поиск похожих документов"""
        try:
            conn = await self._get_connection()
            
            # Базовый запрос
            query = """
                SELECT 
                    c.id, c.doc_id, c.kind, c.content, c.table_html, 
                    c.bbox, c.page_no, c.created_at,
                    1 - (e.embedding <=> %s) AS score
                FROM embeddings e
                JOIN chunks c ON c.id = e.chunk_id
                JOIN documents d ON c.doc_id = d.id
            """
            
            params = [query_vector]
            conditions = []
            
            # Фильтр по тенанту
            if tenant_id:
                conditions.append("d.tenant_id = %s")
                params.append(tenant_id)
            
            # Дополнительные фильтры
            if filters:
                if "mime_type" in filters:
                    conditions.append("d.mime_type = %s")
                    params.append(filters["mime_type"])
                
                if "kind" in filters:
                    conditions.append("c.kind = %s")
                    params.append(filters["kind"])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY e.embedding <=> %s LIMIT %s"
            params.extend([query_vector, top_k])
            
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Конвертируем в список словарей
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error searching similar: {e}")
            return []
    
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Получить чанки документа"""
        try:
            conn = await self._get_connection()
            
            query = """
                SELECT 
                    c.id, c.chunk_index, c.kind, c.content, 
                    c.table_html, c.bbox, c.page_no, c.created_at
                FROM chunks c
                WHERE c.doc_id = %s
                ORDER BY c.chunk_index
            """
            
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, [doc_id])
                results = cur.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            return []
    
    async def get_document_info(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о документе"""
        try:
            conn = await self._get_connection()
            
            query = """
                SELECT 
                    d.id, d.title, d.source_path, d.mime_type, 
                    d.sha256, d.size_bytes, d.tenant_id, d.created_at, d.meta,
                    COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.doc_id
                WHERE d.id = %s
                GROUP BY d.id
            """
            
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, [doc_id])
                result = cur.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error getting document info: {e}")
            return None
    
    async def list_documents(
        self, 
        tenant_id: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """Получить список документов с пагинацией"""
        try:
            conn = await self._get_connection()
            
            # Подсчет общего количества
            count_query = "SELECT COUNT(*) FROM documents"
            count_params = []
            
            if tenant_id:
                count_query += " WHERE tenant_id = %s"
                count_params.append(tenant_id)
            
            with conn.cursor() as cur:
                cur.execute(count_query, count_params)
                total = cur.fetchone()[0]
            
            # Получение документов
            offset = (page - 1) * size
            query = """
                SELECT 
                    d.id, d.title, d.source_path, d.mime_type, 
                    d.sha256, d.size_bytes, d.tenant_id, d.created_at, d.meta,
                    COUNT(c.id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.id = c.doc_id
            """
            
            params = []
            if tenant_id:
                query += " WHERE d.tenant_id = %s"
                params.append(tenant_id)
            
            query += """
                GROUP BY d.id
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([size, offset])
            
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                documents = [dict(row) for row in results]
            
            return {
                "documents": documents,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {"documents": [], "total": 0, "page": page, "size": size, "pages": 0}
