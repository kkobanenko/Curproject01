"""
Streamlit приложение для RAG-платформы
Основные функции: поиск, чат, загрузка документов
"""

import streamlit as st
import requests
import json
from typing import List, Dict, Any
import os

# Настройка страницы
st.set_page_config(
    page_title="RAG Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Конфигурация
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8081")

def main():
    """Основная функция приложения"""
    
    # Заголовок
    st.title("🤖 RAG Platform")
    st.markdown("Платформа для семантического поиска и генерации ответов на основе документов")
    
    # Боковая панель
    with st.sidebar:
        st.header("Навигация")
        page = st.selectbox(
            "Выберите раздел",
            ["🏠 Главная", "🔍 Поиск", "💬 RAG Чат", "📁 Документы", "📊 Статистика"]
        )
        
        st.divider()
        
        # Статус сервисов
        st.subheader("Статус сервисов")
        if st.button("Проверить статус"):
            check_services_status()
    
    # Основной контент
    if page == "🏠 Главная":
        show_home_page()
    elif page == "🔍 Поиск":
        show_search_page()
    elif page == "💬 RAG Чат":
        show_chat_page()
    elif page == "📁 Документы":
        show_documents_page()
    elif page == "📊 Статистика":
        show_statistics_page()

def show_home_page():
    """Главная страница"""
    st.header("Добро пожаловать в RAG Platform!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Возможности")
        st.markdown("""
        - **Семантический поиск** по документам
        - **RAG чат** с контекстом из документов
        - **Загрузка документов** различных форматов
        - **OCR обработка** изображений и сканов
        - **Извлечение таблиц** с сохранением структуры
        """)
    
    with col2:
        st.subheader("📋 Поддерживаемые форматы")
        st.markdown("""
        - **PDF** (векторные и сканы)
        - **DOCX** (Word документы)
        - **XLSX** (Excel таблицы)
        - **HTML** (веб-страницы)
        - **EML** (электронная почта)
        - **Изображения** (JPG, PNG, TIFF)
        """)
    
    st.divider()
    
    # Быстрый поиск
    st.subheader("🔍 Быстрый поиск")
    quick_query = st.text_input("Введите запрос для поиска:", placeholder="Например: отчет за 2024 год")
    
    if st.button("Найти"):
        if quick_query:
            perform_search(quick_query)
        else:
            st.warning("Введите текст для поиска")

def show_search_page():
    """Страница поиска"""
    st.header("🔍 Семантический поиск")
    
    # Форма поиска
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input("Поисковый запрос:", placeholder="Введите ваш запрос...")
        
        with col2:
            top_k = st.number_input("Количество результатов:", min_value=1, max_value=50, value=10)
        
        submitted = st.form_submit_button("🔍 Найти")
        
        if submitted and query:
            perform_search(query, top_k)
    
    st.divider()
    
    # История поиска
    if "search_history" not in st.session_state:
        st.session_state.search_history = []
    
    if st.session_state.search_history:
        st.subheader("📚 История поиска")
        for i, (query, timestamp) in enumerate(st.session_state.search_history[-5:]):
            if st.button(f"🔍 {query[:50]}...", key=f"history_{i}"):
                perform_search(query, top_k)

def show_chat_page():
    """Страница RAG чата"""
    st.header("💬 RAG Чат")
    
    # Инициализация истории чата
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Отображение истории чата
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])
    
    # Ввод сообщения
    user_input = st.chat_input("Задайте вопрос...")
    
    if user_input:
        # Добавляем сообщение пользователя
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        
        # Генерируем ответ
        with st.spinner("Генерирую ответ..."):
            response = generate_rag_response(user_input)
            
            if response:
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.chat_message("assistant").write(response)
            else:
                st.error("Ошибка при генерации ответа")

def show_documents_page():
    """Страница управления документами"""
    st.header("📁 Управление документами")
    
    # Загрузка документов
    st.subheader("📤 Загрузка документов")
    
    uploaded_files = st.file_uploader(
        "Выберите файлы для загрузки",
        type=["pdf", "docx", "xlsx", "html", "eml", "jpg", "jpeg", "png", "tiff"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("🚀 Загрузить документы"):
            upload_documents(uploaded_files)
    
    st.divider()
    
    # Список документов
    st.subheader("📚 Загруженные документы")
    if st.button("🔄 Обновить список"):
        load_documents_list()

def show_statistics_page():
    """Страница статистики"""
    st.header("📊 Статистика платформы")
    
    if st.button("🔄 Обновить статистику"):
        load_statistics()

def perform_search(query: str, top_k: int = 10):
    """Выполнение поиска"""
    try:
        with st.spinner("🔍 Выполняю поиск..."):
            response = requests.post(
                f"{API_BASE_URL}/api/v1/search",
                json={"query": query, "top_k": top_k}
            )
            
            if response.status_code == 200:
                results = response.json()
                display_search_results(results)
                
                # Добавляем в историю
                if "search_history" not in st.session_state:
                    st.session_state.search_history = []
                st.session_state.search_history.append((query, "now"))
                
            else:
                st.error(f"Ошибка поиска: {response.status_code}")
                
    except Exception as e:
        st.error(f"Ошибка при выполнении поиска: {str(e)}")

def display_search_results(results: List[Dict[str, Any]]):
    """Отображение результатов поиска"""
    st.subheader(f"📋 Результаты поиска ({len(results)} найдено)")
    
    for i, result in enumerate(results):
        with st.expander(f"📄 {result.get('title', 'Без названия')} (Схожесть: {result.get('score', 0):.2f})"):
            st.markdown(f"**Содержание:** {result.get('content', 'Нет содержимого')}")
            
            if result.get('table_html'):
                st.markdown("**Таблица:**")
                st.html(result.get('table_html'))
            
            st.markdown(f"**Страница:** {result.get('page_no', 'Не указана')}")
            st.markdown(f"**Тип:** {result.get('kind', 'text')}")

def generate_rag_response(query: str) -> str:
    """Генерация RAG ответа"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={"message": query}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "Не удалось сгенерировать ответ")
        else:
            return f"Ошибка API: {response.status_code}"
            
    except Exception as e:
        return f"Ошибка: {str(e)}"

def upload_documents(files):
    """Загрузка документов"""
    try:
        with st.spinner("📤 Загружаю документы..."):
            for file in files:
                files_data = {"file": (file.name, file.getvalue(), file.type)}
                
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/upload",
                    files=files_data
                )
                
                if response.status_code == 200:
                    st.success(f"✅ {file.name} загружен успешно")
                else:
                    st.error(f"❌ Ошибка загрузки {file.name}: {response.status_code}")
                    
    except Exception as e:
        st.error(f"Ошибка при загрузке документов: {str(e)}")

def load_documents_list():
    """Загрузка списка документов"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/documents")
        
        if response.status_code == 200:
            documents = response.json()
            st.dataframe(documents)
        else:
            st.error(f"Ошибка загрузки списка: {response.status_code}")
            
    except Exception as e:
        st.error(f"Ошибка: {str(e)}")

def load_statistics():
    """Загрузка статистики"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/stats")
        
        if response.status_code == 200:
            stats = response.json()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Документы", stats.get("vector_store", {}).get("total_documents", 0))
            
            with col2:
                st.metric("Чанки", stats.get("vector_store", {}).get("total_chunks", 0))
            
            with col3:
                st.metric("Эмбеддинги", stats.get("vector_store", {}).get("total_embeddings", 0))
            
            # Детальная статистика
            st.subheader("📈 Детальная статистика")
            st.json(stats)
            
        else:
            st.error(f"Ошибка загрузки статистики: {response.status_code}")
            
    except Exception as e:
        st.error(f"Ошибка: {str(e)}")

def check_services_status():
    """Проверка статуса сервисов"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        
        if response.status_code == 200:
            health = response.json()
            status = health.get("status", "unknown")
            
            if status == "healthy":
                st.success("✅ Все сервисы работают")
            elif status == "degraded":
                st.warning("⚠️ Некоторые сервисы недоступны")
            else:
                st.error("❌ Сервисы недоступны")
            
            # Детали
            details = health.get("details", {})
            for service, status in details.items():
                if status:
                    st.success(f"✅ {service}")
                else:
                    st.error(f"❌ {service}")
                    
        else:
            st.error(f"❌ API недоступен: {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ Ошибка проверки статуса: {str(e)}")

if __name__ == "__main__":
    main()
