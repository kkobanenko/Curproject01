"""
Компонент для работы с документами
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd


class DocumentList:
    """Список документов"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
    
    def render(self):
        """Отображение списка документов"""
        st.header("📚 Документы")
        
        # Параметры отображения
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            page = st.number_input("Страница", min_value=1, value=1)
        
        with col2:
            size = st.selectbox("Размер страницы", [10, 20, 50, 100])
        
        with col3:
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        
        # Фильтры
        with st.expander("🔍 Фильтры"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.multiselect(
                    "Статус",
                    ["uploaded", "processing", "completed", "failed"],
                    default=["completed"],
                    format_func=lambda x: {
                        "uploaded": "Загружен",
                        "processing": "Обрабатывается",
                        "completed": "Завершен",
                        "failed": "Ошибка"
                    }[x]
                )
                
                mime_type_filter = st.multiselect(
                    "Тип файла",
                    ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/html", "text/plain"],
                    default=[],
                    format_func=lambda x: {
                        "application/pdf": "PDF",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
                        "text/html": "HTML",
                        "text/plain": "TXT"
                    }[x]
                )
            
            with col2:
                date_from = st.date_input(
                    "Дата загрузки с",
                    value=None
                )
                
                date_to = st.date_input(
                    "Дата загрузки по",
                    value=None
                )
            
            with col3:
                tags_filter = st.multiselect(
                    "Теги",
                    ["важное", "контракт", "отчет", "анализ", "финансы", "юридический", "технический"],
                    default=[]
                )
                
                min_size = st.number_input(
                    "Минимальный размер (MB)",
                    min_value=0,
                    value=0
                )
        
        # Получение списка документов
        with st.spinner("Загружаются документы..."):
            data = self._get_documents(
                page=page,
                size=size,
                status_filter=status_filter,
                mime_type_filter=mime_type_filter,
                date_from=date_from,
                date_to=date_to,
                tags_filter=tags_filter,
                min_size=min_size
            )
            
            if "error" in data:
                st.error(f"Ошибка получения документов: {data['error']}")
                return
            
            # Статистика
            total_docs = data.get('total', 0)
            if total_docs > 0:
                st.success(f"📊 Всего документов: {total_docs}")
                
                # Отображение документов
                self._render_documents(data.get('documents', []))
                
                # Пагинация
                pages = data.get('pages', 1)
                if pages > 1:
                    st.write(f"📄 Страница {data.get('page', 1)} из {pages}")
                    
                    # Навигация по страницам
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        if page > 1:
                            if st.button("⬅️ Предыдущая"):
                                st.session_state.current_page = page - 1
                                st.rerun()
                    
                    with col3:
                        st.write(f"**{page}**")
                    
                    with col5:
                        if page < pages:
                            if st.button("Следующая ➡️"):
                                st.session_state.current_page = page + 1
                                st.rerun()
            else:
                st.info("📭 Нет документов, соответствующих фильтрам")
    
    def _get_documents(self, **kwargs) -> Dict[str, Any]:
        """Получение списка документов"""
        try:
            # Формируем параметры запроса
            params = {
                "page": kwargs["page"],
                "size": kwargs["size"]
            }
            
            # Добавляем фильтры
            if kwargs["status_filter"]:
                params["status"] = ",".join(kwargs["status_filter"])
            
            if kwargs["mime_type_filter"]:
                params["mime_type"] = ",".join(kwargs["mime_type_filter"])
            
            if kwargs["date_from"]:
                params["date_from"] = kwargs["date_from"].isoformat()
            
            if kwargs["date_to"]:
                params["date_to"] = kwargs["date_to"].isoformat()
            
            if kwargs["tags_filter"]:
                params["tags"] = ",".join(kwargs["tags_filter"])
            
            if kwargs["min_size"] > 0:
                params["min_size"] = kwargs["min_size"] * 1024 * 1024  # Конвертируем в байты
            
            # Выполняем запрос
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/documents",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.json().get("detail", "Неизвестная ошибка")
                return {"error": f"Ошибка получения документов: {error_msg}"}
                
        except requests.exceptions.Timeout:
            return {"error": "Превышено время ожидания"}
        except requests.exceptions.ConnectionError:
            return {"error": "Ошибка соединения с API"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка: {str(e)}"}
    
    def _render_documents(self, documents: List[Dict[str, Any]]):
        """Отображение списка документов"""
        for i, doc in enumerate(documents):
            self._render_document(doc, i)
    
    def _render_document(self, doc: Dict[str, Any], index: int):
        """Отображение отдельного документа"""
        # Определяем иконку по типу файла
        mime_type = doc.get('mime_type', '')
        if 'pdf' in mime_type:
            icon = "📄"
        elif 'word' in mime_type:
            icon = "📝"
        elif 'spreadsheet' in mime_type:
            icon = "📊"
        elif 'html' in mime_type:
            icon = "🌐"
        elif 'text' in mime_type:
            icon = "📃"
        else:
            icon = "📎"
        
        # Определяем цвет по статусу
        status = doc.get('status', 'unknown')
        if status == 'completed':
            status_color = "success"
            status_icon = "✅"
        elif status == 'processing':
            status_color = "info"
            status_icon = "⏳"
        elif status == 'failed':
            status_color = "error"
            status_icon = "❌"
        else:
            status_color = "warning"
            status_icon = "⚠️"
        
        # Заголовок документа
        title = doc.get('title', 'Без названия')
        with st.expander(f"{icon} {title} {status_icon}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Основная информация
                st.write(f"**ID:** {doc.get('id', 'N/A')}")
                st.write(f"**Путь:** {doc.get('source_path', 'N/A')}")
                st.write(f"**Тип:** {doc.get('mime_type', 'N/A')}")
                st.write(f"**Чанков:** {doc.get('chunk_count', 0)}")
                
                # Теги
                tags = doc.get('tags', [])
                if tags:
                    st.write("**Теги:**")
                    for tag in tags:
                        st.write(f"- {tag}")
                
                # Описание
                description = doc.get('description', '')
                if description:
                    st.write("**Описание:**")
                    st.write(description)
            
            with col2:
                # Техническая информация
                st.write(f"**Размер:** {doc.get('size_bytes', 'N/A')} байт")
                st.write(f"**Загружен:** {doc.get('created_at', 'N/A')}")
                if doc.get('sha256'):
                    st.write(f"**SHA256:** {doc['sha256'][:16]}...")
                
                # Статус обработки
                st.write(f"**Статус:** {status_icon} {status}")
                
                # Прогресс обработки
                if status == 'processing':
                    progress = doc.get('processing_progress', 0)
                    st.progress(progress / 100)
                    st.write(f"Прогресс: {progress}%")
            
            # Дополнительная информация
            with st.expander("📊 Детальная информация"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Метаданные:**")
                    metadata = doc.get('metadata', {})
                    if metadata:
                        for key, value in metadata.items():
                            st.write(f"- **{key}:** {value}")
                    else:
                        st.write("Нет метаданных")
                
                with col2:
                    st.write("**Статистика:**")
                    st.write(f"- Страниц: {doc.get('page_count', 'N/A')}")
                    st.write(f"- Таблиц: {doc.get('table_count', 'N/A')}")
                    st.write(f"- Изображений: {doc.get('image_count', 'N/A')}")
                    st.write(f"- Слов: {doc.get('word_count', 'N/A')}")
            
            # Действия с документом
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"👁️ Просмотр", key=f"view_{index}"):
                    st.session_state.selected_document = doc
                    st.switch_page("👁️ Просмотр документа")
            
            with col2:
                if st.button(f"🔍 Чанки", key=f"chunks_{index}"):
                    st.session_state.selected_document = doc
                    st.switch_page("🔍 Чанки документа")
            
            with col3:
                if st.button(f"📊 Анализ", key=f"analyze_{index}"):
                    st.session_state.selected_document = doc
                    st.switch_page("📊 Анализ документа")
            
            with col4:
                if st.button(f"🗑️ Удалить", key=f"delete_{index}"):
                    if self._delete_document(doc.get('id')):
                        st.success("✅ Документ удален")
                        st.rerun()
                    else:
                        st.error("❌ Ошибка удаления")
    
    def _delete_document(self, doc_id: str) -> bool:
        """Удаление документа"""
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.delete(
                f"{self.api_base_url}/api/v1/documents/{doc_id}",
                headers=headers,
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"Ошибка удаления: {str(e)}")
            return False


class DocumentViewer:
    """Просмотр документа"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
    
    def render(self, document: Dict[str, Any]):
        """Отображение документа для просмотра"""
        st.header(f"👁️ Просмотр документа: {document.get('title', 'Без названия')}")
        
        # Навигация
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Назад к списку"):
                st.switch_page("📚 Документы")
        
        with col2:
            st.write(f"**ID:** {document.get('id', 'N/A')} | **Статус:** {document.get('status', 'N/A')}")
        
        with col3:
            if st.button("🔄 Обновить"):
                st.rerun()
        
        # Основная информация
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Общая информация")
            st.write(f"**Название:** {document.get('title', 'N/A')}")
            st.write(f"**Описание:** {document.get('description', 'N/A')}")
            st.write(f"**Путь:** {document.get('source_path', 'N/A')}")
            st.write(f"**Тип:** {document.get('mime_type', 'N/A')}")
            
            # Теги
            tags = document.get('tags', [])
            if tags:
                st.write("**Теги:**")
                for tag in tags:
                    st.write(f"- {tag}")
        
        with col2:
            st.subheader("📊 Статистика")
            st.write(f"**Размер:** {document.get('size_bytes', 'N/A')} байт")
            st.write(f"**Страниц:** {document.get('page_count', 'N/A')}")
            st.write(f"**Чанков:** {document.get('chunk_count', 'N/A')}")
            st.write(f"**Таблиц:** {document.get('table_count', 'N/A')}")
            st.write(f"**Изображений:** {document.get('image_count', 'N/A')}")
            st.write(f"**Слов:** {document.get('word_count', 'N/A')}")
        
        # Содержимое документа
        st.subheader("📖 Содержимое")
        
        # Выбор страницы
        page_count = document.get('page_count', 1)
        if page_count > 1:
            selected_page = st.selectbox(
                "Выберите страницу",
                range(1, page_count + 1),
                index=0
            )
        else:
            selected_page = 1
        
        # Получение содержимого страницы
        content = self._get_page_content(document.get('id'), selected_page)
        
        if content:
            # Отображение содержимого
            if content.get('type') == 'text':
                st.write("**Текст:**")
                st.write(content.get('content', ''))
            
            elif content.get('type') == 'table':
                st.write("**Таблица:**")
                table_data = content.get('table_data', [])
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df)
                else:
                    st.write("Данные таблицы недоступны")
            
            elif content.get('type') == 'image':
                st.write("**Изображение:**")
                image_url = content.get('image_url')
                if image_url:
                    st.image(image_url)
                else:
                    st.write("Изображение недоступно")
            
            # Метаданные страницы
            if content.get('metadata'):
                with st.expander("📋 Метаданные страницы"):
                    metadata = content['metadata']
                    for key, value in metadata.items():
                        st.write(f"**{key}:** {value}")
        else:
            st.info("Содержимое страницы недоступно")
        
        # Действия с документом
        st.subheader("🔧 Действия")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Поиск в документе"):
                st.info("Функция поиска в документе в разработке")
        
        with col2:
            if st.button("💬 Чат о документе"):
                st.info("Функция чата о документе в разработке")
        
        with col3:
            if st.button("📊 Экспорт"):
                st.info("Функция экспорта в разработке")
        
        with col4:
            if st.button("📋 Копировать"):
                st.success("✅ Информация скопирована в буфер обмена")
    
    def _get_page_content(self, doc_id: str, page: int) -> Optional[Dict[str, Any]]:
        """Получение содержимого страницы"""
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/documents/{doc_id}/pages/{page}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            st.error(f"Ошибка получения содержимого: {str(e)}")
            return None
