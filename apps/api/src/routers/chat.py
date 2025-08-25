"""
Роутер для чата с RAG
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from ..schemas.chat import ChatRequest, ChatResponse
from ..services.rag_pipeline import RAGPipeline

router = APIRouter()

# Зависимости
async def get_rag_pipeline() -> RAGPipeline:
    """Получить RAG пайплайн"""
    return RAGPipeline()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """Чат с RAG системой"""
    try:
        # Генерируем ответ через RAG пайплайн
        result = await rag_pipeline.generate_answer(
            query=request.message,
            top_k=request.top_k,
            use_rerank=request.use_context,  # Используем rerank если включен контекст
            tenant_id=request.tenant_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Генерируем ID беседы если не передан
        conversation_id = request.conversation_id or f"conv_{hash(request.message) % 1000000}"
        
        return ChatResponse(
            message=result["message"],
            conversation_id=conversation_id,
            citations=result["citations"],
            processing_time=result["processing_time"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_with_rag_stream(
    request: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """Стриминг чата с RAG системой"""
    try:
        # Пока возвращаем обычный ответ
        # В будущем можно реализовать стриминг
        result = await rag_pipeline.generate_answer(
            query=request.message,
            top_k=request.top_k,
            use_rerank=request.use_context,
            tenant_id=request.tenant_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        conversation_id = request.conversation_id or f"conv_{hash(request.message) % 1000000}"
        
        return ChatResponse(
            message=result["message"],
            conversation_id=conversation_id,
            citations=result["citations"],
            processing_time=result["processing_time"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{conversation_id}")
async def get_chat_history(conversation_id: str):
    """Получить историю беседы"""
    try:
        # TODO: Реализовать получение истории беседы
        # Пока возвращаем заглушку
        
        return {
            "conversation_id": conversation_id,
            "messages": [],
            "total_messages": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/history/{conversation_id}")
async def clear_chat_history(conversation_id: str):
    """Очистить историю беседы"""
    try:
        # TODO: Реализовать очистку истории
        # Пока возвращаем заглушку
        
        return {
            "message": "Chat history cleared",
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
