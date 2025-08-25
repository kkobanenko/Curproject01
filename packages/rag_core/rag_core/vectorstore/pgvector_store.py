"""
Векторное хранилище на основе PostgreSQL + pgvector
Поддерживает HNSW индексы для быстрого ANN-поиска
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import uuid
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

class PgVectorStore:
    """Полнофункциональное векторное хранилище на PostgreSQL с pgvector"""
    
    def __init__(self, dsn: str, 
                 embedding_dim: int = 1024,
                 create_tables: bool = True):
        self.dsn = dsn
        self.embedding_dim = embedding_dim
        self._check_connection()
        
        if create_tables:
            self._ensure_schema()
    
    def _check_connection(self):
        """Проверяет соединение с базой данных"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Проверяем расширение pgvector
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    if not cur.fetchone():
                        logger.warning("pgvector extension not found. Please install it first.")
                    
                    # Проверяем версию PostgreSQL
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
                    logger.info(f"Connected to PostgreSQL: {version}")
                    
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _ensure_schema(self):
        """Создает необходимые таблицы и индексы"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Создаем таблицы если их нет
                    self._create_tables(cur)
                    self._create_indexes(cur)
                    conn.commit()
                    logger.info("Database schema ensured successfully")
                    
        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            raise
    
    def _create_tables(self, cur):
        """Создает необходимые таблицы"""
        # Таблица тенантов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        
        # Таблица ролей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        
        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                email TEXT UNIQUE NOT NULL,
                role_id UUID REFERENCES roles(id),
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        
        # Таблица документов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                title TEXT,
                source_path TEXT,
                mime_type TEXT,
                sha256 TEXT UNIQUE,
                size_bytes BIGINT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                meta JSONB DEFAULT '{}'::jsonb,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Таблица чанков
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_type TEXT NOT NULL,
                content TEXT,
                table_html TEXT,
                bbox JSONB,
                page_no INTEGER,
                created_at TIMESTAMPTZ DEFAULT now(),
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # Таблица эмбеддингов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
                embedding vector(%s) NOT NULL,
                model_name TEXT DEFAULT 'bge-m3',
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """, (self.embedding_dim,))
        
        # Таблица ACL
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doc_acl (
                doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
                can_read BOOLEAN NOT NULL DEFAULT TRUE,
                can_write BOOLEAN NOT NULL DEFAULT FALSE,
                can_delete BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (doc_id, role_id)
            )
        """)
        
        # Таблица поисковых запросов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_text TEXT NOT NULL,
                user_id UUID REFERENCES users(id),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                results_count INTEGER,
                search_time_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        
        # Вставляем дефолтные данные
        self._insert_default_data(cur)
    
    def _insert_default_data(self, cur):
        """Вставляет дефолтные данные"""
        # Дефолтный тенант
        cur.execute("""
            INSERT INTO tenants (code, name) 
            VALUES ('default', 'Default Tenant')
            ON CONFLICT (code) DO NOTHING
        """)
        
        # Дефолтные роли
        roles = [
            ('admin', 'Administrator'),
            ('user', 'Regular User'),
            ('viewer', 'Read-only User')
        ]
        
        for role_code, role_name in roles:
            cur.execute("""
                INSERT INTO roles (name, description) 
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (role_code, role_name))
    
    def _create_indexes(self, cur):
        """Создает необходимые индексы"""
        # Индекс на SHA256 документов
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_sha256 
            ON documents(sha256)
        """)
        
        # Индекс на tenant_id документов
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_tenant 
            ON documents(tenant_id)
        """)
        
        # Индекс на chunk_type
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_type 
            ON chunks(chunk_type)
        """)
        
        # Индекс на page_no
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_page 
            ON chunks(page_no)
        """)
        
        # HNSW индекс для векторного поиска
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw 
            ON embeddings USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        
        # Индекс на модель эмбеддингов
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_model 
            ON embeddings(model_name)
        """)
        
        # Составной индекс для ACL
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_acl_role 
            ON doc_acl(role_id, can_read)
        """)
    
    def get_default_tenant_id(self) -> str:
        """Получает ID дефолтного тенанта"""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tenants WHERE code = 'default' LIMIT 1")
                row = cur.fetchone()
                if row:
                    return str(row[0])
                else:
                    # Создаем дефолтный тенант если его нет
                    cur.execute("""
                        INSERT INTO tenants (code, name) 
                        VALUES ('default', 'Default Tenant') 
                        RETURNING id
                    """)
                    return str(cur.fetchone()[0])
    
    def ensure_document(self, 
                       source_path: str, 
                       sha256: str, 
                       title: str = None,
                       mime_type: str = None,
                       size_bytes: int = None,
                       tenant_id: str = None,
                       metadata: Dict[str, Any] = None) -> str:
        """Создает или обновляет документ"""
        if tenant_id is None:
            tenant_id = self.get_default_tenant_id()
        
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO documents (tenant_id, title, source_path, sha256, mime_type, size_bytes, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sha256) DO UPDATE SET
                        title = EXCLUDED.title,
                        source_path = EXCLUDED.source_path,
                        mime_type = EXCLUDED.mime_type,
                        size_bytes = EXCLUDED.size_bytes,
                        meta = EXCLUDED.meta,
                        updated_at = now()
                    RETURNING id
                """, (tenant_id, title, source_path, sha256, mime_type, size_bytes, 
                      json.dumps(metadata or {})))
                
                doc_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Document ensured: {doc_id}")
                return str(doc_id)
    
    def upsert_chunks_and_embeddings(self, 
                                    doc_id: str, 
                                    chunks: List[Dict[str, Any]], 
                                    embeddings: List[List[float]],
                                    model_name: str = 'bge-m3') -> List[str]:
        """Добавляет чанки и их эмбеддинги"""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        chunk_ids = []
        
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for chunk_data, embedding in zip(chunks, embeddings):
                    # Вставляем чанк
                    cur.execute("""
                        INSERT INTO chunks (doc_id, chunk_index, chunk_type, content, table_html, bbox, page_no, meta)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        doc_id,
                        chunk_data.get('chunk_index', 0),
                        chunk_data.get('chunk_type', 'text'),
                        chunk_data.get('content'),
                        chunk_data.get('table_html'),
                        json.dumps(chunk_data.get('bbox')),
                        chunk_data.get('page_no'),
                        json.dumps(chunk_data.get('metadata', {}))
                    ))
                    
                    chunk_id = cur.fetchone()[0]
                    chunk_ids.append(str(chunk_id))
                    
                    # Вставляем эмбеддинг
                    cur.execute("""
                        INSERT INTO embeddings (chunk_id, embedding, model_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_name = EXCLUDED.model_name,
                            created_at = now()
                    """, (chunk_id, embedding, model_name))
                
                conn.commit()
                logger.info(f"Upserted {len(chunk_ids)} chunks with embeddings")
        
        return chunk_ids
    
    def search(self, 
               query_vector: List[float], 
               top_k: int = 20,
               filters: Dict[str, Any] = None,
               user_role: str = None,
               tenant_id: str = None) -> List[Dict[str, Any]]:
        """Выполняет семантический поиск с фильтрами"""
        if tenant_id is None:
            tenant_id = self.get_default_tenant_id()
        
        # Базовый SQL запрос
        sql = """
            SELECT 
                c.id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.table_html,
                c.bbox,
                c.page_no,
                c.meta as chunk_meta,
                d.title,
                d.source_path,
                d.mime_type,
                d.meta as doc_meta,
                1 - (e.embedding <=> %s) AS similarity_score
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            JOIN documents d ON d.id = c.doc_id
            WHERE d.tenant_id = %s
        """
        
        params = [query_vector, tenant_id]
        param_count = 2
        
        # Добавляем фильтры
        if filters:
            sql, params, param_count = self._add_search_filters(sql, params, param_count, filters)
        
        # Добавляем ACL фильтры
        if user_role:
            sql, params, param_count = self._add_acl_filters(sql, params, param_count, user_role)
        
        # Завершаем запрос
        sql += """
            ORDER BY e.embedding <=> %s
            LIMIT %s
        """
        params.extend([query_vector, top_k])
        
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    results = cur.fetchall()
                    
                    # Конвертируем в словари
                    search_results = []
                    for row in results:
                        result = dict(row)
                        # Конвертируем UUID в строки
                        result['id'] = str(result['id'])
                        result['doc_id'] = str(result['doc_id'])
                        search_results.append(result)
                    
                    logger.info(f"Search returned {len(search_results)} results")
                    return search_results
                    
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _add_search_filters(self, sql: str, params: List, param_count: int, filters: Dict[str, Any]) -> Tuple[str, List, int]:
        """Добавляет фильтры поиска к SQL запросу"""
        conditions = []
        
        # Фильтр по типу чанка
        if 'chunk_type' in filters:
            param_count += 1
            conditions.append(f"c.chunk_type = %s")
            params.append(filters['chunk_type'])
        
        # Фильтр по MIME типу документа
        if 'mime_type' in filters:
            param_count += 1
            conditions.append(f"d.mime_type = %s")
            params.append(filters['mime_type'])
        
        # Фильтр по странице
        if 'page_no' in filters:
            param_count += 1
            conditions.append(f"c.page_no = %s")
            params.append(filters['page_no'])
        
        # Фильтр по размеру документа
        if 'min_size' in filters:
            param_count += 1
            conditions.append(f"d.size_bytes >= %s")
            params.append(filters['min_size'])
        
        if 'max_size' in filters:
            param_count += 1
            conditions.append(f"d.size_bytes <= %s")
            params.append(filters['max_size'])
        
        # Фильтр по дате создания
        if 'created_after' in filters:
            param_count += 1
            conditions.append(f"d.created_at >= %s")
            params.append(filters['created_after'])
        
        if 'created_before' in filters:
            param_count += 1
            conditions.append(f"d.created_at <= %s")
            params.append(filters['created_before'])
        
        # Фильтр по метаданным (JSONB)
        if 'metadata' in filters:
            for key, value in filters['metadata'].items():
                param_count += 1
                conditions.append(f"d.meta->>%s = %s")
                params.extend([key, str(value)])
        
        # Добавляем условия к запросу
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        
        return sql, params, param_count
    
    def _add_acl_filters(self, sql: str, params: List, param_count: int, user_role: str) -> Tuple[str, List, int]:
        """Добавляет ACL фильтры к SQL запросу"""
        # Получаем role_id для пользователя
        role_id = self._get_role_id(user_role)
        if role_id:
            param_count += 1
            sql += " AND EXISTS (SELECT 1 FROM doc_acl da WHERE da.doc_id = d.id AND da.role_id = %s AND da.can_read = TRUE)"
            params.append(role_id)
        
        return sql, params, param_count
    
    def _get_role_id(self, role_name: str) -> Optional[str]:
        """Получает ID роли по имени"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
                    row = cur.fetchone()
                    return str(row[0]) if row else None
        except Exception as e:
            logger.warning(f"Failed to get role ID for {role_name}: {e}")
            return None
    
    def get_document(self, doc_id: str, user_role: str = None) -> Optional[Dict[str, Any]]:
        """Получает документ по ID с проверкой ACL"""
        sql = """
            SELECT 
                d.id,
                d.title,
                d.source_path,
                d.mime_type,
                d.sha256,
                d.size_bytes,
                d.created_at,
                d.updated_at,
                d.meta,
                d.status
            FROM documents d
            WHERE d.id = %s
        """
        
        params = [doc_id]
        
        # Добавляем ACL проверку
        if user_role:
            role_id = self._get_role_id(user_role)
            if role_id:
                sql += " AND EXISTS (SELECT 1 FROM doc_acl da WHERE da.doc_id = d.id AND da.role_id = %s AND da.can_read = TRUE)"
                params.append(role_id)
        
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    row = cur.fetchone()
                    
                    if row:
                        result = dict(row)
                        result['id'] = str(result['id'])
                        return result
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def get_document_chunks(self, doc_id: str, user_role: str = None) -> List[Dict[str, Any]]:
        """Получает все чанки документа с проверкой ACL"""
        sql = """
            SELECT 
                c.id,
                c.chunk_index,
                c.chunk_type,
                c.content,
                c.table_html,
                c.bbox,
                c.page_no,
                c.meta,
                c.created_at
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            WHERE c.doc_id = %s
        """
        
        params = [doc_id]
        
        # Добавляем ACL проверку
        if user_role:
            role_id = self._get_role_id(user_role)
            if role_id:
                sql += " AND EXISTS (SELECT 1 FROM doc_acl da WHERE da.doc_id = d.id AND da.role_id = %s AND da.can_read = TRUE)"
                params.append(role_id)
        
        sql += " ORDER BY c.chunk_index"
        
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    
                    chunks = []
                    for row in rows:
                        chunk = dict(row)
                        chunk['id'] = str(chunk['id'])
                        chunks.append(chunk)
                    
                    return chunks
                    
        except Exception as e:
            logger.error(f"Failed to get chunks for document {doc_id}: {e}")
            return []
    
    def delete_document(self, doc_id: str, user_role: str = None) -> bool:
        """Удаляет документ с проверкой ACL"""
        # Проверяем права на удаление
        if user_role:
            role_id = self._get_role_id(user_role)
            if role_id:
                with psycopg.connect(self.dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT can_delete FROM doc_acl 
                            WHERE doc_id = %s AND role_id = %s
                        """, (doc_id, role_id))
                        row = cur.fetchone()
                        if not row or not row[0]:
                            logger.warning(f"User {user_role} cannot delete document {doc_id}")
                            return False
        
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Удаляем документ (каскадно удалятся чанки и эмбеддинги)
                    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        logger.info(f"Document {doc_id} deleted successfully")
                        return True
                    else:
                        logger.warning(f"Document {doc_id} not found")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def get_statistics(self, tenant_id: str = None) -> Dict[str, Any]:
        """Получает статистику хранилища"""
        if tenant_id is None:
            tenant_id = self.get_default_tenant_id()
        
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Общая статистика
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_documents,
                            COUNT(DISTINCT mime_type) as unique_mime_types,
                            SUM(size_bytes) as total_size_bytes,
                            AVG(size_bytes) as avg_size_bytes
                        FROM documents 
                        WHERE tenant_id = %s AND status = 'active'
                    """, (tenant_id,))
                    
                    doc_stats = cur.fetchone()
                    
                    # Статистика чанков
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_chunks,
                            COUNT(DISTINCT chunk_type) as unique_chunk_types,
                            COUNT(DISTINCT page_no) as total_pages
                        FROM chunks c
                        JOIN documents d ON d.id = c.doc_id
                        WHERE d.tenant_id = %s AND d.status = 'active'
                    """, (tenant_id,))
                    
                    chunk_stats = cur.fetchone()
                    
                    # Статистика эмбеддингов
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_embeddings,
                            COUNT(DISTINCT model_name) as unique_models
                        FROM embeddings e
                        JOIN chunks c ON c.id = e.chunk_id
                        JOIN documents d ON d.id = c.doc_id
                        WHERE d.tenant_id = %s AND d.status = 'active'
                    """, (tenant_id,))
                    
                    embedding_stats = cur.fetchone()
                    
                    return {
                        'documents': {
                            'total': doc_stats[0],
                            'unique_mime_types': doc_stats[1],
                            'total_size_bytes': doc_stats[2] or 0,
                            'avg_size_bytes': doc_stats[3] or 0
                        },
                        'chunks': {
                            'total': chunk_stats[0],
                            'unique_types': chunk_stats[1],
                            'total_pages': chunk_stats[2] or 0
                        },
                        'embeddings': {
                            'total': embedding_stats[0],
                            'unique_models': embedding_stats[1]
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def optimize_indexes(self) -> bool:
        """Оптимизирует индексы для лучшей производительности"""
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # VACUUM ANALYZE для обновления статистики
                    cur.execute("VACUUM ANALYZE")
                    
                    # REINDEX для пересоздания индексов
                    cur.execute("REINDEX INDEX CONCURRENTLY idx_embeddings_hnsw")
                    
                    conn.commit()
                    logger.info("Index optimization completed successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            return False
