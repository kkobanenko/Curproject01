#!/usr/bin/env python3
"""
Простой тест для проверки базовой функциональности Streamlit
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Тест импортов основных модулей"""
    try:
        import streamlit as st
        print("✅ Streamlit импортирован успешно")
        
        # Проверяем, что можем импортировать main
        from main import main
        print("✅ Основная функция импортирована успешно")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_functions():
    """Тест основных функций"""
    try:
        from main import check_api_health, search_documents, chat_with_rag
        
        print("✅ Основные функции импортированы успешно")
        
        # Проверяем, что функции существуют
        assert callable(check_api_health)
        assert callable(search_documents)
        assert callable(chat_with_rag)
        
        print("✅ Все функции являются callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка функций: {e}")
        return False

def test_ui_components():
    """Тест UI компонентов"""
    try:
        from main import show_search_page, show_chat_page, show_upload_page, show_documents_page
        
        print("✅ UI компоненты импортированы успешно")
        
        # Проверяем, что функции существуют
        assert callable(show_search_page)
        assert callable(show_chat_page)
        assert callable(show_upload_page)
        assert callable(show_documents_page)
        
        print("✅ Все UI компоненты являются callable")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка UI компонентов: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование RAG Platform Streamlit...")
    print("=" * 50)
    
    tests = [
        ("Импорты", test_imports),
        ("Функции", test_functions),
        ("UI компоненты", test_ui_components),
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
