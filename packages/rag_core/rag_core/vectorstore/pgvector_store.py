"""
Векторное хранилище на основе PostgreSQL + pgvector
Поддерживает HNSW индексы для быстрого ANN-поиска
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import psycopg
from psycopg.types import Json

@dataclass
class SearchResult:
    """Результат поиска"""
    chunk_id: str
    doc_id: str
    kind: str
    content: str
    table_html: Optional[str]
    score: float
    bbox: Optional[Dict[str, Any]]
    page_no: Optional[int]
    metadata: Optional[Dict[str, Any]]

class PgVectorStore:
    """Векторное хранилище на основе pgvector"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._ensure_extension()
    
    def _ensure_extension(self):
        """Проверка и включение расширения pgvector"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Проверяем, включено ли расширение
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    if not cur.fetchone():
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        logging.info("pgvector extension created")
                    
                    # Проверяем версию pgvector
                    cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                    version = cur.fetchone()
                    if version:
                        logging.info(f"pgvector version: {version[0]}")
                    
        except Exception as e:
            logging.error(f"Error ensuring pgvector extension: {e}")
            raise
    
    def _default_tenant_id(self, cur) -> str:
        """Получение ID дефолтного тенанта"""
        cur.execute("SELECT id FROM tenants WHERE code = 'default' LIMIT 1")
        row = cur.fetchone()
        if row:
            return row[0]
        
        # Fallback - создаем дефолтный тенант если его нет
        cur.execute(
            "INSERT INTO tenants (code, name) VALUES ('default', 'Default Tenant') RETURNING id"
        )
        return cur.fetchone()[0]
    
    def ensure_document(self, path: str, sha256: str, title: str, 
                       mime_type: Optional[str] = None, size_bytes: Optional[int] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Создание или обновление документа"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                tenant_id = self._default_tenant_id(cur)
                
                cur.execute(
                    """
                    INSERT INTO documents (tenant_id, title, source_path, sha256, mime_type, size_bytes, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sha256) DO UPDATE SET 
                        title = EXCLUDED.title,
                        source_path = EXCLUDED.source_path,
                        mime_type = EXCLUDED.mime_type,
                        size_bytes = EXCLUDED.size_bytes,
                        meta = EXCLUDED.meta
                    RETURNING id
                    """,
                    (tenant_id, title, path, sha256, mime_type, size_bytes, 
                     Json(metadata) if metadata else None)
                )
                return cur.fetchone()[0]
    
    def upsert_chunks_and_embeddings(self, doc_id: str, payloads: List[Dict[str, Any]], 
                                    vectors: List[List[float]]):
        """Добавление чанков и их эмбеддингов"""
        assert len(payloads) == len(vectors), "Payloads and vectors must have same length"
        
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for payload, vector in zip(payloads, vectors):
                    # Вставляем чанк
                    cur.execute(
                        """
                        INSERT INTO chunks (doc_id, chunk_index, kind, content, table_html, bbox, page_no)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            doc_id,
                            payload.get("idx", 0),
                            payload.get("kind", "text"),
                            payload.get("text"),
                            payload.get("table_html"),
                            Json(payload.get("bbox")) if payload.get("bbox") else None,
                            payload.get("page_no")
                        )
                    )
                    chunk_id = cur.fetchone()[0]
                    
                    # Вставляем эмбеддинг
                    cur.execute(
                        "INSERT INTO embeddings (chunk_id, embedding) VALUES (%s, %s)",
                        (chunk_id, vector)
                    )
            
            conn.commit()
            logging.info(f"Upserted {len(payloads)} chunks with embeddings for document {doc_id}")
    
    def search(self, query_vector: List[float], top_k: int = 20, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Поиск по векторным эмбеддингам"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                # Базовый запрос
                query = """
                    SELECT 
                        c.id, c.doc_id, c.kind, c.content, c.table_html, 
                        1 - (e.embedding <=> %s) AS score,
                        c.bbox, c.page_no, c.metadata
                    FROM embeddings e
                    JOIN chunks c ON c.id = e.chunk_id
                    JOIN documents d ON d.id = c.doc_id
                """
                
                params = [query_vector]
                conditions = []
                
                # Применяем фильтры
                if filters:
                    if 'tenant_id' in filters:
                        conditions.append("d.tenant_id = %s")
                        params.append(filters['tenant_id'])
                    
                    if 'doc_id' in filters:
                        conditions.append("c.doc_id = %s")
                        params.append(filters['doc_id'])
                    
                    if 'kind' in filters:
                        conditions.append("c.kind = %s")
                        params.append(filters['kind'])
                    
                    if 'min_confidence' in filters:
                        conditions.append("c.metadata->>'confidence' >= %s")
                        params.append(str(filters['min_confidence']))
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # Добавляем сортировку и лимит
                query += " ORDER BY e.embedding <=> %s LIMIT %s"
                params.extend([query_vector, top_k])
                
                # Выполняем запрос
                cur.execute(query, params)
                
                # Формируем результаты
                results = []
                for row in cur.fetchall():
                    result = SearchResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        kind=row[2],
                        content=row[3],
                        table_html=row[4],
                        score=row[5],
                        bbox=row[6] if row[6] else None,
                        page_no=row[7],
                        metadata=row[8] if row[8] else None
                    )
                    results.append(result)
                
                return results
    
    def search_similar(self, chunk_id: str, top_k: int = 10) -> List[SearchResult]:
        """Поиск похожих чанков"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                # Получаем эмбеддинг для заданного чанка
                cur.execute(
                    "SELECT embedding FROM embeddings WHERE chunk_id = %s",
                    (chunk_id,)
                )
                row = cur.fetchone()
                if not row:
                    return []
                
                query_vector = row[0]
                
                # Ищем похожие чанки
                cur.execute(
                    """
                    SELECT 
                        c.id, c.doc_id, c.kind, c.content, c.table_html,
                        1 - (e.embedding <=> %s) AS score,
                        c.bbox, c.page_no, c.metadata
                    FROM embeddings e
                    JOIN chunks c ON c.id = e.chunk_id
                    WHERE e.chunk_id != %s
                    ORDER BY e.embedding <=> %s
                    LIMIT %s
                    """,
                    (query_vector, chunk_id, query_vector, top_k)
                )
                
                results = []
                for row in cur.fetchall():
                    result = SearchResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        kind=row[2],
                        content=row[3],
                        table_html=row[4],
                        score=row[5],
                        bbox=row[6] if row[6] else None,
                        page_no=row[7],
                        metadata=row[8] if row[8] else None
                    )
                    results.append(result)
                
                return results
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Получение всех чанков документа"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        c.id, c.chunk_index, c.kind, c.content, c.table_html,
                        c.bbox, c.page_no, c.metadata
                    FROM chunks c
                    WHERE c.doc_id = %s
                    ORDER BY c.chunk_index
                    """,
                    (doc_id,)
                )
                
                chunks = []
                for row in cur.fetchall():
                    chunk = {
                        'id': row[0],
                        'chunk_index': row[1],
                        'kind': row[2],
                        'content': row[3],
                        'table_html': row[4],
                        'bbox': row[5],
                        'page_no': row[6],
                        'metadata': row[7]
                    }
                    chunks.append(chunk)
                
                return chunks
    
    def delete_document(self, doc_id: str) -> bool:
        """Удаление документа и всех его чанков"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Удаляем эмбеддинги (каскадно удалятся чанки)
                    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                    deleted_count = cur.rowcount
                    
                    conn.commit()
                    logging.info(f"Deleted document {doc_id} with {deleted_count} chunks")
                    return deleted_count > 0
                    
        except Exception as e:
            logging.error(f"Error deleting document {doc_id}: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики хранилища"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                stats = {}
                
                # Количество документов
                cur.execute("SELECT COUNT(*) FROM documents")
                stats['total_documents'] = cur.fetchone()[0]
                
                # Количество чанков
                cur.execute("SELECT COUNT(*) FROM chunks")
                stats['total_chunks'] = cur.fetchone()[0]
                
                # Количество эмбеддингов
                cur.execute("SELECT COUNT(*) FROM embeddings")
                stats['total_embeddings'] = cur.fetchone()[0]
                
                # Размер эмбеддингов
                cur.execute("SELECT COUNT(*) FROM embeddings LIMIT 1")
                if cur.fetchone():
                    cur.execute("SELECT embedding FROM embeddings LIMIT 1")
                    sample_embedding = cur.fetchone()[0]
                    stats['embedding_dimension'] = len(sample_embedding)
                
                # Распределение по типам чанков
                cur.execute(
                    "SELECT kind, COUNT(*) FROM chunks GROUP BY kind"
                )
                stats['chunks_by_kind'] = dict(cur.fetchall())
                
                # Распределение по тенантам
                cur.execute(
                    "SELECT t.code, COUNT(d.id) FROM tenants t LEFT JOIN documents d ON t.id = d.tenant_id GROUP BY t.id, t.code"
                )
                stats['documents_by_tenant'] = dict(cur.fetchall())
                
                return stats
    
    def create_indexes(self):
        """Создание индексов для оптимизации"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # HNSW индекс для векторного поиска
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw 
                        ON embeddings USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                    """)
                    
                    # Индексы для метаданных
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id 
                        ON chunks (doc_id)
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_chunks_kind 
                        ON chunks (kind)
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_documents_tenant_id 
                        ON documents (tenant_id)
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_documents_sha256 
                        ON documents (sha256)
                    """)
                    
                    conn.commit()
                    logging.info("Database indexes created successfully")
                    
        except Exception as e:
            logging.error(f"Error creating indexes: {e}")
            raise
    
    def optimize_database(self):
        """Оптимизация базы данных"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # VACUUM ANALYZE для обновления статистики
                    cur.execute("VACUUM ANALYZE")
                    conn.commit()
                    logging.info("Database optimization completed")
                    
        except Exception as e:
            logging.error(f"Error optimizing database: {e}")
            raise
