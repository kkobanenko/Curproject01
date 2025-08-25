"""
Streamlit приложение для RAG платформы
"""
import streamlit as st
import requests
import json
from typing import List, Dict, Any
import os

# Настройки
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8081")

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


def check_api_health() -> bool:
    """Проверка доступности API"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def search_documents(query: str, top_k: int = 20) -> Dict[str, Any]:
    """Поиск документов"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json={"query": query, "top_k": top_k}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Search failed: {response.status_code}"}
    except Exception as e:
        return {"error": f"Search error: {str(e)}"}


def chat_with_rag(message: str, top_k: int = 5) -> Dict[str, Any]:
    """Чат с RAG системой"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={
                "message": message,
                "top_k": top_k,
                "use_context": True
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Chat failed: {response.status_code}"}
    except Exception as e:
        return {"error": f"Chat error: {str(e)}"}


def upload_document(file, title: str = None) -> Dict[str, Any]:
    """Загрузка документа"""
    try:
        files = {"file": file}
        data = {"title": title} if title else {}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/upload",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Upload failed: {response.status_code}"}
    except Exception as e:
        return {"error": f"Upload error: {str(e)}"}


def main():
    """Основная функция приложения"""
    
    # Заголовок
    st.title("🔍 RAG Platform")
    st.markdown("Платформа для семантического поиска и анализа документов")
    
    # Проверка API
    if not check_api_health():
        st.error("❌ API недоступен. Проверьте, что сервис запущен.")
        st.stop()
    
    # Боковая панель
    with st.sidebar:
        st.header("Навигация")
        
        page = st.selectbox(
            "Выберите раздел",
            ["Поиск", "Чат", "Загрузка", "Документы"]
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
    
    # Основной контент
    if page == "Поиск":
        show_search_page()
    elif page == "Чат":
        show_chat_page()
    elif page == "Загрузка":
        show_upload_page()
    elif page == "Документы":
        show_documents_page()


def show_search_page():
    """Страница поиска"""
    st.header("🔍 Поиск документов")
    
    # Форма поиска
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Поисковый запрос",
                placeholder="Введите ваш запрос...",
                help="Опишите, что вы ищете"
            )
        
        with col2:
            top_k = st.number_input("Количество результатов", min_value=1, max_value=100, value=20)
        
        submitted = st.form_submit_button("🔍 Найти", use_container_width=True)
    
    if submitted and query:
        with st.spinner("Выполняется поиск..."):
            results = search_documents(query, top_k)
            
            if "error" in results:
                st.error(f"Ошибка поиска: {results['error']}")
            else:
                st.success(f"Найдено {results['total']} результатов")
                
                # Отображение результатов
                for i, result in enumerate(results['results']):
                    with st.expander(f"Результат {i+1} (релевантность: {result['score']:.3f})"):
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            st.write(f"**Тип:** {result['kind']}")
                            st.write(f"**Страница:** {result.get('page_no', 'N/A')}")
                        
                        with col2:
                            if result['kind'] == 'table':
                                st.write("**Таблица:**")
                                st.html(result.get('table_html', ''))
                            else:
                                st.write("**Текст:**")
                                st.write(result.get('content', '')[:500] + "..." if len(result.get('content', '')) > 500 else result.get('content', ''))
                
                # Статистика
                st.info(f"⏱️ Время обработки: {results['processing_time']:.3f} сек")


def show_chat_page():
    """Страница чата"""
    st.header("💬 Чат с документами")
    
    # Параметры чата
    col1, col2 = st.columns([3, 1])
    
    with col1:
        user_message = st.text_input(
            "Ваше сообщение",
            placeholder="Задайте вопрос о документах...",
            key="user_input"
        )
    
    with col2:
        top_k = st.number_input("Контекст", min_value=1, max_value=20, value=5)
    
    # Кнопка отправки
    if st.button("💬 Отправить", use_container_width=True) and user_message:
        # Добавляем сообщение пользователя в историю
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Получаем ответ от RAG
        with st.spinner("Генерируется ответ..."):
            response = chat_with_rag(user_message, top_k)
            
            if "error" in response:
                st.error(f"Ошибка чата: {response['error']}")
            else:
                # Добавляем ответ в историю
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response['message']
                })
                
                # Обновляем ID беседы
                st.session_state.current_conversation = response['conversation_id']
        
        # Очищаем поле ввода
        st.rerun()
    
    # Отображение истории чата
    st.subheader("История беседы")
    
    if not st.session_state.chat_history:
        st.info("Начните беседу, отправив первое сообщение")
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])
        
        # Кнопка очистки истории
        if st.button("🗑️ Очистить историю"):
            st.session_state.chat_history = []
            st.session_state.current_conversation = None
            st.rerun()


def show_upload_page():
    """Страница загрузки документов"""
    st.header("📤 Загрузка документов")
    
    # Форма загрузки
    with st.form("upload_form"):
        uploaded_file = st.file_uploader(
            "Выберите файл",
            type=['pdf', 'docx', 'xlsx', 'html', 'txt', 'jpg', 'jpeg', 'png'],
            help="Поддерживаемые форматы: PDF, DOCX, XLSX, HTML, TXT, изображения"
        )
        
        title = st.text_input("Название документа (опционально)")
        
        submitted = st.form_submit_button("📤 Загрузить", use_container_width=True)
    
    if submitted and uploaded_file:
        with st.spinner("Загружается документ..."):
            result = upload_document(uploaded_file, title)
            
            if "error" in result:
                st.error(f"Ошибка загрузки: {result['error']}")
            else:
                st.success("✅ Документ успешно загружен!")
                
                # Информация о загруженном файле
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID файла:** {result['file_id']}")
                    st.write(f"**Имя файла:** {result['filename']}")
                
                with col2:
                    st.write(f"**Размер:** {result['size']} байт")
                    st.write(f"**Тип:** {result['mime_type']}")
                
                st.info("Документ будет обработан в фоновом режиме. Вы можете отслеживать статус в разделе 'Документы'.")


def show_documents_page():
    """Страница документов"""
    st.header("📚 Документы")
    
    # Параметры отображения
    col1, col2 = st.columns([2, 1])
    
    with col1:
        page = st.number_input("Страница", min_value=1, value=1)
    
    with col2:
        size = st.selectbox("Размер страницы", [10, 20, 50, 100])
    
    # Получение списка документов
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/documents",
            params={"page": page, "size": size}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            st.success(f"Всего документов: {data['total']}")
            
            # Отображение документов
            for doc in data['documents']:
                with st.expander(f"📄 {doc.get('title', 'Без названия')}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**ID:** {doc['id']}")
                        st.write(f"**Путь:** {doc.get('source_path', 'N/A')}")
                        st.write(f"**Тип:** {doc.get('mime_type', 'N/A')}")
                        st.write(f"**Чанков:** {doc.get('chunk_count', 0)}")
                    
                    with col2:
                        st.write(f"**Размер:** {doc.get('size_bytes', 'N/A')} байт")
                        st.write(f"**Загружен:** {doc['created_at']}")
                        st.write(f"**SHA256:** {doc['sha256'][:16]}...")
                    
                    # Кнопки действий
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"👁️ Просмотр", key=f"view_{doc['id']}"):
                            st.info("Функция просмотра в разработке")
                    
                    with col2:
                        if st.button(f"🔍 Чанки", key=f"chunks_{doc['id']}"):
                            st.info("Функция просмотра чанков в разработке")
                    
                    with col3:
                        if st.button(f"🗑️ Удалить", key=f"delete_{doc['id']}"):
                            st.info("Функция удаления в разработке")
            
            # Пагинация
            if data['pages'] > 1:
                st.write(f"Страница {data['page']} из {data['pages']}")
        
        else:
            st.error(f"Ошибка получения документов: {response.status_code}")
    
    except Exception as e:
        st.error(f"Ошибка: {str(e)}")


if __name__ == "__main__":
    main()
