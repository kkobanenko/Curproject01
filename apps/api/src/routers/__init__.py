from .search import router as search_router
from .documents import router as documents_router
from .chat import router as chat_router

__all__ = ["search_router", "documents_router", "chat_router"]
