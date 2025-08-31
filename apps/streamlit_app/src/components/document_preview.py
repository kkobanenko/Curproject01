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

# Опциональные импорты для различных форматов документов
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import xml.etree.ElementTree as ET
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
            'json': self._preview_json,
            'xml': self._preview_xml,
            'csv': self._preview_csv,
            'png': self._preview_image,
            'jpg': self._preview_image,
            'jpeg': self._preview_image,
            'gif': self._preview_image,
            'bmp': self._preview_image,
            'tiff': self._preview_image,
            'webp': self._preview_image
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
                    
                    # Настройки отображения
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Основная таблица
                        st.dataframe(df, use_container_width=True)
                    
                    with col2:
                        # Статистика листа
                        st.metric("Строк", len(df))
                        st.metric("Столбцов", len(df.columns))
                        st.metric("Ячеек", len(df) * len(df.columns))
                        
                        # Информация о данных
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            st.write("**Числовые столбцы:**")
                            for col in numeric_cols[:5]:  # Показываем первые 5
                                st.write(f"• {col}")
                        
                        # Пропущенные значения
                        missing_data = df.isnull().sum().sum()
                        if missing_data > 0:
                            st.warning(f"Пропущенных значений: {missing_data}")
                        else:
                            st.success("✅ Пропущенных значений нет")
                    
                    # Дополнительная информация
                    with st.expander("📈 Анализ данных", expanded=False):
                        if len(numeric_cols) > 0:
                            st.write("**Описательная статистика:**")
                            st.dataframe(df[numeric_cols].describe())
                        
                        # Корреляционная матрица для числовых данных
                        if len(numeric_cols) > 1:
                            st.write("**Корреляционная матрица:**")
                            corr_matrix = df[numeric_cols].corr()
                            st.dataframe(corr_matrix)
                else:
                    st.info("Лист пуст или содержит некорректные данные")
        else:
            st.warning("Не удалось извлечь данные из XLSX файла")
    
    def _preview_html(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр HTML документа"""
        st.subheader("🌐 Содержимое HTML")
        
        if content.get('html'):
            # Визуализация HTML
            with st.expander("👁️ Визуализация", expanded=True):
                st.components.v1.html(content['html'], height=600)
            
            # Анализ HTML структуры
            if BS4_AVAILABLE:
                try:
                    soup = BeautifulSoup(content['html'], 'html.parser')
                    
                    # Статистика HTML
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Тегов", len(soup.find_all()))
                    
                    with col2:
                        st.metric("Ссылок", len(soup.find_all('a')))
                    
                    with col3:
                        st.metric("Изображений", len(soup.find_all('img')))
                    
                    with col4:
                        st.metric("Таблиц", len(soup.find_all('table')))
                    
                    # Извлеченные ссылки
                    links = soup.find_all('a', href=True)
                    if links:
                        with st.expander("🔗 Ссылки", expanded=False):
                            for i, link in enumerate(links[:10]):  # Показываем первые 10
                                st.write(f"{i+1}. [{link.get_text().strip()}]({link['href']})")
                    
                    # Извлеченные изображения
                    images = soup.find_all('img', src=True)
                    if images:
                        with st.expander("🖼️ Изображения", expanded=False):
                            for i, img in enumerate(images[:5]):  # Показываем первые 5
                                st.write(f"{i+1}. {img['src']}")
                                if img.get('alt'):
                                    st.caption(f"Alt: {img['alt']}")
                    
                    # Таблицы
                    tables = soup.find_all('table')
                    if tables:
                        with st.expander("📊 Таблицы", expanded=False):
                            for i, table in enumerate(tables):
                                st.write(f"**Таблица {i+1}:**")
                                try:
                                    df = pd.read_html(str(table))[0]
                                    st.dataframe(df, use_container_width=True)
                                except:
                                    st.write("Не удалось преобразовать в таблицу")
                                
                except Exception as e:
                    st.warning(f"Ошибка анализа HTML: {str(e)}")
            
            # Исходный HTML код
            with st.expander("🔍 Исходный HTML", expanded=False):
                st.code(content['html'], language='html')
        
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
    
    def _preview_xml(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр XML документа"""
        st.subheader("🔧 Содержимое XML")
        
        if content.get('xml') or content.get('text'):
            xml_content = content.get('xml', content.get('text', ''))
            
            # Валидация и форматирование XML
            if XML_AVAILABLE:
                try:
                    root = ET.fromstring(xml_content)
                    
                    # Статистика XML
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Элементов", len(root.findall('.//')))
                    
                    with col2:
                        st.metric("Атрибутов", len(root.findall('.//[@*]')))
                    
                    with col3:
                        st.metric("Уровней вложенности", self._get_xml_depth(root))
                    
                    # Структура XML
                    with st.expander("🏗️ Структура XML", expanded=False):
                        self._display_xml_structure(root)
                    
                except ET.ParseError as e:
                    st.error(f"Ошибка парсинга XML: {str(e)}")
            
            # Исходный XML код
            with st.expander("🔍 Исходный XML", expanded=True):
                st.code(xml_content, language='xml')
        else:
            st.warning("XML содержимое не найдено")
    
    def _preview_csv(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр CSV документа"""
        st.subheader("📊 Содержимое CSV")
        
        if content.get('text') or content.get('data'):
            csv_content = content.get('text', '')
            
            if csv_content:
                try:
                    # Попытка определить разделитель
                    import csv as csv_module
                    from io import StringIO
                    
                    # Пробуем разные разделители
                    separators = [',', ';', '\t', '|']
                    best_separator = ','
                    best_score = 0
                    
                    for sep in separators:
                        try:
                            reader = csv_module.reader(StringIO(csv_content), delimiter=sep)
                            rows = list(reader)
                            if len(rows) > 1 and len(rows[0]) > 1:
                                score = len(rows[0])
                                if score > best_score:
                                    best_score = score
                                    best_separator = sep
                        except:
                            continue
                    
                    # Читаем CSV с лучшим разделителем
                    df = pd.read_csv(StringIO(csv_content), sep=best_separator)
                    
                    # Отображение данных
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.dataframe(df, use_container_width=True)
                    
                    with col2:
                        st.metric("Строк", len(df))
                        st.metric("Столбцов", len(df.columns))
                        st.metric("Разделитель", best_separator)
                        
                        # Информация о типах данных
                        st.write("**Типы данных:**")
                        for col in df.columns:
                            dtype = str(df[col].dtype)
                            st.write(f"• {col}: {dtype}")
                    
                    # Анализ данных
                    with st.expander("📈 Анализ данных", expanded=False):
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            st.write("**Описательная статистика:**")
                            st.dataframe(df[numeric_cols].describe())
                        
                        # Пропущенные значения
                        missing_data = df.isnull().sum()
                        if missing_data.sum() > 0:
                            st.write("**Пропущенные значения:**")
                            st.dataframe(missing_data[missing_data > 0])
                        else:
                            st.success("✅ Пропущенных значений нет")
                    
                except Exception as e:
                    st.error(f"Ошибка обработки CSV: {str(e)}")
                    # Показываем как текст
                    st.text_area("Содержимое", value=csv_content, height=300, disabled=True)
            else:
                st.warning("CSV содержимое не найдено")
    
    def _preview_image(self, content: Dict[str, Any], document_info: Dict[str, Any]):
        """Предпросмотр изображения"""
        st.subheader("🖼️ Предпросмотр изображения")
        
        if content.get('image_data') or content.get('data'):
            image_data = content.get('image_data', content.get('data', ''))
            
            try:
                if isinstance(image_data, str):
                    # Base64 декодирование
                    if image_data.startswith('data:image'):
                        # Убираем data URL префикс
                        image_data = image_data.split(',')[1]
                    
                    img_bytes = base64.b64decode(image_data)
                else:
                    img_bytes = image_data
                
                # Отображение изображения
                st.image(img_bytes, caption=document_info.get('title', 'Изображение'))
                
                # Информация об изображении
                if PIL_AVAILABLE:
                    try:
                        img = Image.open(BytesIO(img_bytes))
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Ширина", f"{img.width}px")
                        
                        with col2:
                            st.metric("Высота", f"{img.height}px")
                        
                        with col3:
                            st.metric("Формат", img.format)
                        
                        with col4:
                            st.metric("Режим", img.mode)
                        
                        # Дополнительная информация
                        with st.expander("📋 Дополнительная информация", expanded=False):
                            st.write(f"**Размер файла:** {len(img_bytes)} байт")
                            st.write(f"**Соотношение сторон:** {img.width/img.height:.2f}")
                            
                            if hasattr(img, '_getexif') and img._getexif():
                                st.write("**EXIF данные:**")
                                exif = img._getexif()
                                for tag, value in exif.items():
                                    st.write(f"• {tag}: {value}")
                    
                    except Exception as e:
                        st.warning(f"Не удалось получить информацию об изображении: {str(e)}")
                
            except Exception as e:
                st.error(f"Ошибка отображения изображения: {str(e)}")
        else:
            st.warning("Данные изображения не найдены")
    
    def _get_xml_depth(self, element, depth=0):
        """Получение максимальной глубины XML"""
        if not element:
            return depth
        
        max_depth = depth
        for child in element:
            child_depth = self._get_xml_depth(child, depth + 1)
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _display_xml_structure(self, element, level=0):
        """Отображение структуры XML"""
        indent = "  " * level
        tag_name = element.tag
        attributes = " ".join([f'{k}="{v}"' for k, v in element.attrib.items()])
        
        if attributes:
            st.write(f"{indent}<{tag_name} {attributes}>")
        else:
            st.write(f"{indent}<{tag_name}>")
        
        # Показываем только первые несколько уровней
        if level < 3:
            for child in element[:5]:  # Показываем только первые 5 детей
                self._display_xml_structure(child, level + 1)
        
        if level == 0 and len(element) > 5:
            st.write(f"{indent}  ... и еще {len(element) - 5} элементов")
