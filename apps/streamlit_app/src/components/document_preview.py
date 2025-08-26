"""
Компонент для предпросмотра документов
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, Optional, List
import requests
import base64
from io import BytesIO
import fitz  # PyMuPDF
from docx import Document
import xml.etree.ElementTree as ET
import re


class DocumentPreview:
    """Компонент для предпросмотра документов различных форматов"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.supported_formats = {
            'pdf': self._preview_pdf,
            'docx': self._preview_docx,
            'xlsx': self._preview_xlsx,
            'html': self._preview_html,
            'txt': self._preview_text,
            'json': self._preview_json
        }
    
    def render(self, document_id: str, document_info: Dict[str, Any]):
        """Основной метод рендеринга предпросмотра"""
        st.header(f"📄 {document_info.get('title', 'Документ')}")
        
        # Метаданные документа
        self._render_metadata(document_info)
        
        # Навигация по страницам/разделам
        if document_info.get('total_pages', 1) > 1:
            self._render_page_navigation(document_info)
        
        # Предпросмотр содержимого
        self._render_content_preview(document_id, document_info)
        
        # Дополнительные действия
        self._render_actions(document_id, document_info)
    
    def _render_metadata(self, document_info: Dict[str, Any]):
        """Отображение метаданных документа"""
        with st.expander("📋 Метаданные", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Основная информация:**")
                st.write(f"• Тип: {document_info.get('file_type', 'Неизвестно')}")
                st.write(f"• Размер: {document_info.get('file_size', 'Неизвестно')}")
                st.write(f"• Загружен: {document_info.get('uploaded_at', 'Неизвестно')}")
                st.write(f"• Автор: {document_info.get('author', 'Неизвестно')}")
            
            with col2:
                st.write("**Статистика:**")
                st.write(f"• Страниц: {document_info.get('total_pages', 1)}")
                st.write(f"• Чанков: {document_info.get('chunks_count', 0)}")
                st.write(f"• Слов: {document_info.get('word_count', 0)}")
                st.write(f"• Таблиц: {document_info.get('tables_count', 0)}")
    
    def _render_page_navigation(self, document_info: Dict[str, Any]):
        """Навигация по страницам документа"""
        total_pages = document_info.get('total_pages', 1)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            current_page = st.selectbox(
                "Страница",
                range(1, total_pages + 1),
                index=0,
                key=f"page_select_{document_info.get('id')}"
            )
        
        # Отображение прогресса
        progress = current_page / total_pages
        st.progress(progress)
        st.caption(f"Страница {current_page} из {total_pages}")
    
    def _render_content_preview(self, document_id: str, document_info: Dict[str, Any]):
        """Предпросмотр содержимого документа"""
        file_type = document_info.get('file_type', '').lower()
        
        # Получаем содержимое документа
        content = self._get_document_content(document_id)
        
        if not content:
            st.error("Не удалось загрузить содержимое документа")
            return
        
        # Выбираем метод предпросмотра
        preview_method = self.supported_formats.get(file_type, self._preview_generic)
        preview_method(content, document_info)
    
    def _get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Получение содержимого документа из API"""
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/documents/{document_id}/content",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Ошибка получения содержимого: {response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"Ошибка соединения: {str(e)}")
            return None
    
    def _preview_pdf(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр PDF документа"""
        st.subheader("📄 Содержимое PDF")
        
        # Отображение текста
        if content.get('text'):
            with st.expander("📝 Текст документа", expanded=True):
                st.text_area(
                    "Содержимое",
                    value=content['text'],
                    height=300,
                    disabled=True,
                    key=f"pdf_text_{document_info.get('id')}"
                )
        
        # Отображение таблиц
        if content.get('tables'):
            st.subheader("📊 Таблицы")
            for i, table in enumerate(content['tables']):
                with st.expander(f"Таблица {i+1}", expanded=False):
                    if table.get('data'):
                        df = pd.DataFrame(table['data'])
                        st.dataframe(df, use_container_width=True)
                    
                    if table.get('html'):
                        st.components.v1.html(table['html'], height=400)
        
        # Отображение изображений
        if content.get('images'):
            st.subheader("🖼️ Изображения")
            for i, image in enumerate(content['images']):
                if image.get('data'):
                    try:
                        img_data = base64.b64decode(image['data'])
                        st.image(img_data, caption=f"Изображение {i+1}")
                    except:
                        st.error(f"Ошибка отображения изображения {i+1}")
    
    def _preview_docx(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр DOCX документа"""
        st.subheader("📝 Содержимое DOCX")
        
        if content.get('text'):
            with st.expander("📝 Текст документа", expanded=True):
                st.text_area(
                    "Содержимое",
                    value=content['text'],
                    height=300,
                    disabled=True,
                    key=f"docx_text_{document_info.get('id')}"
                )
        
        # Отображение таблиц
        if content.get('tables'):
            st.subheader("📊 Таблицы")
            for i, table in enumerate(content['tables']):
                with st.expander(f"Таблица {i+1}", expanded=False):
                    if table.get('data'):
                        df = pd.DataFrame(table['data'])
                        st.dataframe(df, use_container_width=True)
    
    def _preview_xlsx(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр XLSX документа"""
        st.subheader("📊 Содержимое XLSX")
        
        if content.get('sheets'):
            # Выбор листа
            sheet_names = list(content['sheets'].keys())
            selected_sheet = st.selectbox(
                "Выберите лист",
                sheet_names,
                key=f"sheet_select_{document_info.get('id')}"
            )
            
            if selected_sheet and content['sheets'][selected_sheet]:
                sheet_data = content['sheets'][selected_sheet]
                
                if isinstance(sheet_data, list) and len(sheet_data) > 0:
                    df = pd.DataFrame(sheet_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Статистика листа
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Строк", len(df))
                    with col2:
                        st.metric("Столбцов", len(df.columns))
                    with col3:
                        st.metric("Ячеек", len(df) * len(df.columns))
                else:
                    st.info("Лист пуст или содержит некорректные данные")
    
    def _preview_html(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр HTML документа"""
        st.subheader("🌐 Содержимое HTML")
        
        if content.get('html'):
            with st.expander("🔍 Исходный HTML", expanded=False):
                st.code(content['html'], language='html')
            
            with st.expander("👁️ Визуализация", expanded=True):
                st.components.v1.html(content['html'], height=600)
        
        if content.get('text'):
            with st.expander("📝 Извлеченный текст", expanded=False):
                st.text_area(
                    "Текст",
                    value=content['text'],
                    height=200,
                    disabled=True
                )
    
    def _preview_text(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр текстового документа"""
        st.subheader("📝 Содержимое текстового документа")
        
        if content.get('text'):
            st.text_area(
                "Содержимое",
                value=content['text'],
                height=400,
                disabled=True,
                key=f"text_content_{document_info.get('id')}"
            )
    
    def _preview_json(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр JSON документа"""
        st.subheader("🔧 Содержимое JSON")
        
        if content.get('data'):
            st.json(content['data'])
        
        if content.get('text'):
            with st.expander("📝 Текстовое представление", expanded=False):
                st.text_area(
                    "JSON текст",
                    value=content['text'],
                    height=200,
                    disabled=True
                )
    
    def _preview_generic(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Универсальный предпросмотр для неизвестных форматов"""
        st.subheader("📄 Содержимое документа")
        
        # Пытаемся отобразить как JSON
        try:
            st.json(content)
        except:
            # Если не JSON, показываем как текст
            if content.get('text'):
                st.text_area(
                    "Содержимое",
                    value=content['text'],
                    height=300,
                    disabled=True
                )
            else:
                st.info("Формат документа не поддерживается для предпросмотра")
    
    def _render_actions(self, document_id: str, document_info: Dict[str, Any]):
        """Отображение дополнительных действий"""
        st.divider()
        st.subheader("🔧 Действия")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📥 Скачать", key=f"download_{document_id}"):
                self._download_document(document_id, document_info)
        
        with col2:
            if st.button("🔍 Поиск в документе", key=f"search_in_{document_id}"):
                self._search_in_document(document_id)
        
        with col3:
            if st.button("📊 Анализ", key=f"analyze_{document_id}"):
                self._analyze_document(document_id, document_info)
        
        with col4:
            if st.button("💬 Чат по документу", key=f"chat_{document_id}"):
                self._chat_about_document(document_id, document_info)
    
    def _download_document(self, document_id: str, document_info: Dict[str, Any]):
        """Скачивание документа"""
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/documents/{document_id}/download",
                headers=headers
            )
            
            if response.status_code == 200:
                filename = document_info.get('title', f'document_{document_id}')
                st.download_button(
                    label="💾 Скачать файл",
                    data=response.content,
                    file_name=filename,
                    mime=response.headers.get('content-type', 'application/octet-stream'),
                    key=f"download_btn_{document_id}"
                )
            else:
                st.error("Ошибка скачивания документа")
                
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    def _search_in_document(self, document_id: str):
        """Поиск в документе"""
        st.info("🔍 Функция поиска в документе будет доступна в следующем обновлении")
    
    def _analyze_document(self, document_id: str, document_info: Dict[str, Any]):
        """Анализ документа"""
        st.info("📊 Функция анализа документа будет доступна в следующем обновлении")
    
    def _chat_about_document(self, document_id: str, document_info: Dict[str, Any]):
        """Чат по документу"""
        st.info("💬 Функция чата по документу будет доступна в следующем обновлении")
