"""
Роутер для поиска документов
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from ..schemas.search import SearchRequest, SearchResponse
from ..services.rag_pipeline import RAGPipeline
from ..services.vectorstore import VectorStoreService

router = APIRouter()

# Зависимости
async def get_rag_pipeline() -> RAGPipeline:
    """Получить RAG пайплайн"""
    return RAGPipeline()

async def get_vector_store() -> VectorStoreService:
    """Получить сервис векторного хранилища"""
    return VectorStoreService()


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """Поиск документов по семантическому запросу"""
    try:
        result = await rag_pipeline.search_documents(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            tenant_id=request.tenant_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return SearchResponse(
            query=request.query,
            results=result["results"],
            total=result["total"],
            processing_time=result["processing_time"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/similar/{doc_id}")
async def find_similar_documents(
    doc_id: str,
    top_k: int = Query(default=10, ge=1, le=50),
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """Поиск документов, похожих на указанный"""
    try:
        # Получаем чанки документа
        chunks = await vector_store.get_document_chunks(doc_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Пока возвращаем чанки документа
        # В будущем можно реализовать поиск похожих документов
        return {
            "doc_id": doc_id,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20)
):
    """Получить предложения для поиска"""
    # Простая реализация - возвращаем варианты запроса
    # В будущем можно подключить автодополнение
    suggestions = [
        f"{query} документ",
        f"{query} таблица",
        f"{query} информация",
        f"{query} данные",
        f"{query} отчет"
    ]
    
    return {
        "query": query,
        "suggestions": suggestions[:limit]
    }
