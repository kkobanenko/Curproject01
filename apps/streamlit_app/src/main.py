"""
Streamlit приложение для RAG платформы
"""
import streamlit as st
import requests
import json
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import time

# Импорт компонентов
from components.auth import LoginForm, UserProfile
from components.search import SearchForm, SearchResults
from components.chat import ChatInterface
from components.upload import DocumentUploader
from components.documents import DocumentList

# Настройки
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Конфигурация страницы
st.set_page_config(
    page_title="RAG Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Инициализация состояния сессии
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_conversation" not in st.session_state:
    st.session_state.current_conversation = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user_info" not in st.session_state:
    st.session_state.user_info = None

if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False


def check_api_health() -> bool:
    """Проверка доступности API"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False








def search_documents(query: str, top_k: int = 20, token: str = None) -> Dict[str, Any]:
    """Поиск документов"""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json={"query": query, "top_k": top_k},
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка поиска: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}


def chat_with_rag(message: str, top_k: int = 5, token: str = None) -> Dict[str, Any]:
    """Чат с RAG системой"""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        response = requests.post(
            f"{API_BASE_URL}/api/v1/answers/generate",
            json={
                "question": message,
                "top_k": top_k,
                "include_citations": True
            },
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка чата: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}


def upload_document(file, title: str = None, token: str = None) -> Dict[str, Any]:
    """Загрузка документа"""
    try:
        files = {"file": file}
        data = {"title": title} if title else {}
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/documents/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка загрузки: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}


def get_documents(page: int = 1, size: int = 20, token: str = None) -> Dict[str, Any]:
    """Получение списка документов"""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        response = requests.get(
            f"{API_BASE_URL}/api/v1/documents",
            params={"page": page, "size": size},
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка получения документов: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}


def get_user_info(token: str) -> Dict[str, Any]:
    """Получение информации о пользователе"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/auth/me",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ошибка получения данных: {response.status_code}"}
    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}


def show_login_page():
    """Страница входа в систему"""
    login_form = LoginForm(API_BASE_URL)
    result = login_form.render()
    
    if result:
        # Сохраняем токен и информацию о пользователе
        st.session_state.access_token = result["access_token"]
        st.session_state.is_authenticated = True
        
        # Получаем информацию о пользователе
        user_info = get_user_info(result["access_token"])
        if "error" not in user_info:
            st.session_state.user_info = user_info
        
        st.success("✅ Вход выполнен успешно!")
        time.sleep(1)
        st.rerun()


def show_main_interface():
    """Основной интерфейс после аутентификации"""
    
    # Проверяем, что user_info существует
    if not hasattr(st.session_state, 'user_info') or not st.session_state.user_info:
        st.error("❌ Информация о пользователе недоступна. Войдите заново.")
        st.session_state.clear()
        st.rerun()
    
    # Создаем профиль пользователя
    user_profile = UserProfile(st.session_state.user_info)
    user_profile.render_header()
    
    # Боковая панель
    with st.sidebar:
        st.header("Навигация")
        
        page = st.selectbox(
            "Выберите раздел",
            ["🏠 Главная", "🔍 Поиск", "💬 Чат", "📤 Загрузка", "📚 Документы", "⚙️ Настройки"]
        )
        
        st.divider()
        
        # Статус системы
        st.subheader("Статус системы")
        try:
            health_response = requests.get(f"{API_BASE_URL}/health")
            if health_response.status_code == 200:
                health_data = health_response.json()
                st.success(f"✅ {health_data['status']}")
                if health_data.get('details'):
                    for service, status in health_data['details'].items():
                        icon = "✅" if status else "❌"
                        st.text(f"{icon} {service}")
            else:
                st.error("❌ Неизвестный статус")
        except:
            st.error("❌ Не удалось получить статус")
        
        # Профиль пользователя в боковой панели
        user_profile.render_sidebar()
    
    # Основной контент
    if page == "🏠 Главная":
        show_home_page()
    elif page == "🔍 Поиск":
        show_search_page()
    elif page == "💬 Чат":
        show_chat_page()
    elif page == "📤 Загрузка":
        show_upload_page()
    elif page == "📚 Документы":
        show_documents_page()
    elif page == "⚙️ Настройки":
        show_settings_page()


def show_home_page():
    """Главная страница"""
    st.header("🏠 Добро пожаловать в RAG Platform")
    
    # Статистика
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 Документов",
            value="0",  # TODO: получить из API
            delta="+0"
        )
    
    with col2:
        st.metric(
            label="🔍 Поисков",
            value="0",  # TODO: получить из API
            delta="+0"
        )
    
    with col3:
        st.metric(
            label="💬 Сообщений",
            value="0",  # TODO: получить из API
            delta="+0"
        )
    
    with col4:
        st.metric(
            label="⏱️ Время ответа",
            value="0.5s",  # TODO: получить из API
            delta="-0.1s"
        )
    
    st.divider()
    
    # Быстрые действия
    st.subheader("🚀 Быстрые действия")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Начать поиск", use_container_width=True):
            st.switch_page("🔍 Поиск")
    
    with col2:
        if st.button("💬 Открыть чат", use_container_width=True):
            st.switch_page("💬 Чат")
    
    # Последние документы
    st.subheader("📚 Последние документы")
    st.info("Функция в разработке")
    
    # Последние поиски
    st.subheader("🔍 Последние поиски")
    st.info("Функция в разработке")


def show_search_page():
    """Страница поиска"""
    search_form = SearchForm(API_BASE_URL, st.session_state.access_token)
    results = search_form.render()
    
    if results:
        search_results = SearchResults(results)
        search_results.render()


def show_chat_page():
    """Страница чата"""
    chat_interface = ChatInterface(API_BASE_URL, st.session_state.access_token)
    chat_interface.render()


def show_upload_page():
    """Страница загрузки документов"""
    document_uploader = DocumentUploader(API_BASE_URL, st.session_state.access_token)
    document_uploader.render()


def show_documents_page():
    """Страница документов"""
    document_list = DocumentList(API_BASE_URL, st.session_state.access_token)
    document_list.render()


def show_settings_page():
    """Страница настроек"""
    # Проверяем, что user_info существует
    if not hasattr(st.session_state, 'user_info') or not st.session_state.user_info:
        st.error("❌ Информация о пользователе недоступна. Войдите заново.")
        st.session_state.clear()
        st.rerun()
        return
    
    user_profile = UserProfile(st.session_state.user_info)
    user_profile.render_settings_page()


def main():
    """Основная функция приложения"""
    
    # Проверка API
    if not check_api_health():
        st.error("❌ API недоступен. Проверьте, что сервис запущен.")
        st.stop()
    
    # Проверка аутентификации
    if not st.session_state.is_authenticated:
        show_login_page()
    else:
        show_main_interface()


if __name__ == "__main__":
    main()
