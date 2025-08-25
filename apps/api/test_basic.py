#!/usr/bin/env python3
"""
Простой тест для проверки базовой функциональности API
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Тест импортов основных модулей"""
    try:
        from settings import get_settings
        print("✅ Настройки импортированы успешно")
        
        from schemas.common import HealthResponse
        print("✅ Схемы импортированы успешно")
        
        from services.embeddings import EmbeddingService
        print("✅ Сервис эмбеддингов импортирован успешно")
        
        from services.vectorstore import VectorStoreService
        print("✅ Сервис векторного хранилища импортирован успешно")
        
        from services.rag_pipeline import RAGPipeline
        print("✅ RAG пайплайн импортирован успешно")
        
        from routers.search import router as search_router
        print("✅ Роутер поиска импортирован успешно")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_settings():
    """Тест настроек"""
    try:
        from settings import get_settings
        
        settings = get_settings()
        print(f"✅ Настройки загружены: {settings.app_env}")
        print(f"   API порт: {settings.api_port}")
        print(f"   Ollama URL: {settings.ollama_base_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настроек: {e}")
        return False

def test_schemas():
    """Тест схем данных"""
    try:
        from schemas.common import HealthResponse
        from schemas.search import SearchRequest, SearchResponse
        from schemas.documents import DocumentUpload, DocumentInfo
        from schemas.chat import ChatRequest, ChatResponse
        
        # Создаем тестовые объекты
        health = HealthResponse(
            status="healthy",
            message="Test message",
            version="1.0.0"
        )
        print(f"✅ HealthResponse создан: {health.status}")
        
        search_req = SearchRequest(query="test query")
        print(f"✅ SearchRequest создан: {search_req.query}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка схем: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование RAG Platform API...")
    print("=" * 50)
    
    tests = [
        ("Импорты", test_imports),
        ("Настройки", test_settings),
        ("Схемы", test_schemas),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Тест: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} - ПРОЙДЕН")
        else:
            print(f"❌ {test_name} - ПРОВАЛЕН")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    sys.exit(main())
