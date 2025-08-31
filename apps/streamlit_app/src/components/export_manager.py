"""
Компонент для управления экспортом данных
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import io
import base64
from io import BytesIO
import zipfile
import tempfile
import os


class ExportManager:
    """Компонент для управления экспортом данных"""
    
    def __init__(self):
        self.export_formats = {
            'csv': {'name': 'CSV', 'mime': 'text/csv', 'extension': '.csv', 'category': 'Табличные'},
            'excel': {'name': 'Excel', 'mime': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'extension': '.xlsx', 'category': 'Табличные'},
            'json': {'name': 'JSON', 'mime': 'application/json', 'extension': '.json', 'category': 'Структурированные'},
            'xml': {'name': 'XML', 'mime': 'application/xml', 'extension': '.xml', 'category': 'Структурированные'},
            'yaml': {'name': 'YAML', 'mime': 'text/yaml', 'extension': '.yaml', 'category': 'Структурированные'},
            'txt': {'name': 'Текст', 'mime': 'text/plain', 'extension': '.txt', 'category': 'Текстовые'},
            'html': {'name': 'HTML', 'mime': 'text/html', 'extension': '.html', 'category': 'Текстовые'},
            'markdown': {'name': 'Markdown', 'mime': 'text/markdown', 'extension': '.md', 'category': 'Текстовые'},
            'pdf': {'name': 'PDF', 'mime': 'application/pdf', 'extension': '.pdf', 'category': 'Документы'},
            'zip': {'name': 'ZIP архив', 'mime': 'application/zip', 'extension': '.zip', 'category': 'Архивы'},
            'tar': {'name': 'TAR архив', 'mime': 'application/x-tar', 'extension': '.tar', 'category': 'Архивы'},
            'sql': {'name': 'SQL', 'mime': 'application/sql', 'extension': '.sql', 'category': 'Специальные'}
        }
    
    def render(self, data: Any, data_type: str, title: str = "Экспорт данных"):
        """Основной метод рендеринга экспорта"""
        st.header(f"💾 {title}")
        
        # Информация о данных
        self._render_data_info(data, data_type)
        
        # Выбор формата экспорта
        export_format = self._render_format_selection()
        
        # Настройки экспорта
        export_options = self._render_export_options(export_format, data_type)
        
        # Предварительный просмотр
        if export_format != 'zip':
            self._render_preview(data, export_format, export_options)
        
        # Экспорт
        self._render_export_actions(data, export_format, export_options, title)
        
        # Дополнительные опции
        self._render_additional_options(data, data_type)
    
    def _render_data_info(self, data: Any, data_type: str):
        """Отображение информации о данных"""
        with st.expander("📋 Информация о данных", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Тип данных:**")
                st.write(f"• Категория: {data_type}")
                st.write(f"• Размер: {self._get_data_size(data)}")
                st.write(f"• Элементов: {self._count_elements(data)}")
            
            with col2:
                st.write("**Структура:**")
                if isinstance(data, list):
                    st.write(f"• Тип: Список")
                    if data:
                        st.write(f"• Первый элемент: {type(data[0]).__name__}")
                elif isinstance(data, dict):
                    st.write(f"• Тип: Словарь")
                    st.write(f"• Ключи: {', '.join(list(data.keys())[:5])}")
                elif isinstance(data, pd.DataFrame):
                    st.write(f"• Тип: DataFrame")
                    st.write(f"• Размер: {data.shape[0]} × {data.shape[1]}")
                else:
                    st.write(f"• Тип: {type(data).__name__}")
    
    def _get_data_size(self, data: Any) -> str:
        """Получение размера данных"""
        try:
            if isinstance(data, str):
                return f"{len(data)} символов"
            elif isinstance(data, (list, dict)):
                return f"{len(data)} элементов"
            elif isinstance(data, pd.DataFrame):
                return f"{data.shape[0]} × {data.shape[1]}"
            else:
                return "Неизвестно"
        except:
            return "Неизвестно"
    
    def _count_elements(self, data: Any) -> int:
        """Подсчет количества элементов"""
        try:
            if isinstance(data, (list, dict)):
                return len(data)
            elif isinstance(data, pd.DataFrame):
                return data.shape[0] * data.shape[1]
            elif isinstance(data, str):
                return len(data.split())
            else:
                return 1
        except:
            return 0
    
    def _render_format_selection(self) -> str:
        """Выбор формата экспорта"""
        st.subheader("📁 Выбор формата экспорта")
        
        # Группировка форматов по категориям
        format_categories = {}
        for fmt_key, fmt_info in self.export_formats.items():
            category = fmt_info['category']
            if category not in format_categories:
                format_categories[category] = []
            format_categories[category].append(fmt_key)
        
        selected_format = None
        
        for category, formats in format_categories.items():
            st.write(f"**{category}:**")
            cols = st.columns(len(formats))
            
            for i, fmt in enumerate(formats):
                with cols[i]:
                    if st.button(
                        self.export_formats[fmt]['name'],
                        key=f"format_{fmt}",
                        use_container_width=True
                    ):
                        selected_format = fmt
        
        if selected_format:
            st.success(f"✅ Выбран формат: {self.export_formats[selected_format]['name']}")
            return selected_format
        
        # Если формат не выбран, предлагаем по умолчанию
        default_format = st.selectbox(
            "Или выберите формат:",
            list(self.export_formats.keys()),
            format_func=lambda x: self.export_formats[x]['name']
        )
        
        return default_format
    
    def _render_export_options(self, export_format: str, data_type: str) -> Dict[str, Any]:
        """Настройки экспорта"""
        st.subheader("⚙️ Настройки экспорта")
        
        options = {}
        
        if export_format == 'csv':
            options.update(self._get_csv_options())
        elif export_format == 'excel':
            options.update(self._get_excel_options())
        elif export_format == 'json':
            options.update(self._get_json_options())
        elif export_format == 'txt':
            options.update(self._get_txt_options())
        elif export_format == 'html':
            options.update(self._get_html_options())
        elif export_format == 'xml':
            options.update(self._get_xml_options())
        elif export_format == 'zip':
            options.update(self._get_zip_options())
        elif export_format == 'yaml':
            options.update(self._get_yaml_options())
        elif export_format == 'markdown':
            options.update(self._get_markdown_options())
        elif export_format == 'tar':
            options.update(self._get_tar_options())
        elif export_format == 'sql':
            options.update(self._get_sql_options())
        
        # Общие опции
        options.update(self._get_common_options())
        
        return options
    
    def _get_csv_options(self) -> Dict[str, Any]:
        """Опции для CSV экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            delimiter = st.selectbox("Разделитель", [',', ';', '\t', '|'], key="csv_delimiter")
            encoding = st.selectbox("Кодировка", ['utf-8', 'cp1251', 'iso-8859-1'], key="csv_encoding")
        
        with col2:
            include_index = st.checkbox("Включить индекс", value=False, key="csv_index")
            quote_char = st.selectbox("Символ кавычек", ['"', "'"], key="csv_quote")
        
        return {
            'delimiter': delimiter,
            'encoding': encoding,
            'include_index': include_index,
            'quote_char': quote_char
        }
    
    def _get_excel_options(self) -> Dict[str, Any]:
        """Опции для Excel экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            sheet_name = st.text_input("Название листа", value="Sheet1", key="excel_sheet")
            include_index = st.checkbox("Включить индекс", value=False, key="excel_index")
        
        with col2:
            engine = st.selectbox("Движок", ['openpyxl', 'xlsxwriter'], key="excel_engine", help="openpyxl рекомендуется для лучшей совместимости")
            float_format = st.text_input("Формат чисел", value="%.2f", key="excel_float")
        
        return {
            'sheet_name': sheet_name,
            'include_index': include_index,
            'engine': engine,
            'float_format': float_format
        }
    
    def _get_json_options(self) -> Dict[str, Any]:
        """Опции для JSON экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            orient = st.selectbox(
                "Ориентация",
                ['records', 'index', 'columns', 'values', 'split', 'table'],
                key="json_orient"
            )
            indent = st.slider("Отступ", 0, 8, 2, key="json_indent")
        
        with col2:
            ensure_ascii = st.checkbox("Использовать ASCII", value=False, key="json_ascii")
            date_format = st.selectbox("Формат дат", ['iso', 'epoch'], key="json_date")
        
        return {
            'orient': orient,
            'indent': indent,
            'ensure_ascii': ensure_ascii,
            'date_format': date_format
        }
    
    def _get_txt_options(self) -> Dict[str, Any]:
        """Опции для текстового экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            encoding = st.selectbox("Кодировка", ['utf-8', 'cp1251', 'iso-8859-1'], key="txt_encoding")
            line_separator = st.selectbox("Разделитель строк", ['\n', '\r\n', '\r'], key="txt_linesep")
        
        with col2:
            include_metadata = st.checkbox("Включить метаданные", value=True, key="txt_metadata")
            format_type = st.selectbox("Формат", ['Простой', 'Структурированный'], key="txt_format")
        
        return {
            'encoding': encoding,
            'line_separator': line_separator,
            'include_metadata': include_metadata,
            'format_type': format_type
        }
    
    def _get_html_options(self) -> Dict[str, Any]:
        """Опции для HTML экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            include_styles = st.checkbox("Включить стили", value=True, key="html_styles")
            table_id = st.text_input("ID таблицы", value="export_table", key="html_table_id")
        
        with col2:
            css_class = st.text_input("CSS класс", value="table table-striped", key="html_css_class")
            responsive = st.checkbox("Адаптивная таблица", value=True, key="html_responsive")
        
        return {
            'include_styles': include_styles,
            'table_id': table_id,
            'css_class': css_class,
            'responsive': responsive
        }
    
    def _get_xml_options(self) -> Dict[str, Any]:
        """Опции для XML экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            root_name = st.text_input("Корневой элемент", value="data", key="xml_root")
            item_name = st.text_input("Элемент записи", value="item", key="xml_item")
        
        with col2:
            pretty_print = st.checkbox("Красивое форматирование", value=True, key="xml_pretty")
            encoding = st.selectbox("Кодировка", ['utf-8', 'cp1251'], key="xml_encoding")
        
        return {
            'root_name': root_name,
            'item_name': item_name,
            'pretty_print': pretty_print,
            'encoding': encoding
        }
    
    def _get_zip_options(self) -> Dict[str, Any]:
        """Опции для ZIP экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            compression = st.selectbox("Степень сжатия", ['Нет', 'Быстрое', 'Максимальное'], key="zip_compression")
            include_metadata = st.checkbox("Включить метаданные", value=True, key="zip_metadata")
        
        with col2:
            password = st.text_input("Пароль (опционально)", type="password", key="zip_password")
            comment = st.text_input("Комментарий к архиву", key="zip_comment")
        
        return {
            'compression': compression,
            'include_metadata': include_metadata,
            'password': password,
            'comment': comment
        }
    
    def _get_common_options(self) -> Dict[str, Any]:
        """Общие опции экспорта"""
        st.write("**Общие настройки:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            filename = st.text_input(
                "Имя файла",
                value=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                key="common_filename"
            )
            include_timestamp = st.checkbox("Добавить временную метку", value=True, key="common_timestamp")
        
        with col2:
            quality = st.selectbox("Качество", ['Высокое', 'Среднее', 'Низкое'], key="common_quality")
            preview_size = st.slider("Размер предпросмотра", 10, 100, 50, key="common_preview")
        
        return {
            'filename': filename,
            'include_timestamp': include_timestamp,
            'quality': quality,
            'preview_size': preview_size
        }
    
    def _render_preview(self, data: Any, export_format: str, options: Dict[str, Any]):
        """Предварительный просмотр экспорта"""
        st.subheader("👁️ Предварительный просмотр")
        
        try:
            preview_data = self._prepare_preview_data(data, export_format, options)
            
            if preview_data:
                if export_format in ['csv', 'txt']:
                    st.text_area(
                        "Предпросмотр",
                        value=preview_data,
                        height=200,
                        disabled=True,
                        key=f"preview_{export_format}"
                    )
                elif export_format == 'json':
                    st.json(preview_data)
                elif export_format == 'html':
                    st.components.v1.html(preview_data, height=300)
                elif export_format == 'xml':
                    st.code(preview_data, language='xml')
                else:
                    st.write("Предпросмотр недоступен для данного формата")
            else:
                st.warning("Не удалось подготовить предпросмотр")
                
        except Exception as e:
            st.error(f"Ошибка предпросмотра: {str(e)}")
    
    def _prepare_preview_data(self, data: Any, export_format: str, options: Dict[str, Any]) -> Optional[str]:
        """Подготовка данных для предпросмотра"""
        try:
            preview_size = options.get('preview_size', 50)
            
            if export_format == 'csv':
                if isinstance(data, pd.DataFrame):
                    return data.head(preview_size).to_csv(
                        sep=options.get('delimiter', ','),
                        index=options.get('include_index', False)
                    )
                elif isinstance(data, list):
                    df = pd.DataFrame(data[:preview_size])
                    return df.to_csv(
                        sep=options.get('delimiter', ','),
                        index=options.get('include_index', False)
                    )
            
            elif export_format == 'json':
                if isinstance(data, list):
                    return json.dumps(data[:preview_size], indent=options.get('indent', 2), ensure_ascii=options.get('ensure_ascii', False))
                elif isinstance(data, dict):
                    return json.dumps(data, indent=options.get('indent', 2), ensure_ascii=options.get('ensure_ascii', False))
            
            elif export_format == 'txt':
                if isinstance(data, list):
                    return '\n'.join([str(item) for item in data[:preview_size]])
                elif isinstance(data, str):
                    return data[:preview_size * 10]  # Примерно 10 символов на элемент
            
            elif export_format == 'html':
                if isinstance(data, pd.DataFrame):
                    return data.head(preview_size).to_html(
                        table_id=options.get('table_id', 'export_table'),
                        classes=options.get('css_class', 'table table-striped'),
                        index=options.get('include_index', False)
                    )
            
            elif export_format == 'xml':
                if isinstance(data, list):
                    root_name = options.get('root_name', 'data')
                    item_name = options.get('item_name', 'item')
                    xml_content = f'<{root_name}>\n'
                    for item in data[:preview_size]:
                        xml_content += f'  <{item_name}>{item}</{item_name}>\n'
                    xml_content += f'</{root_name}>'
                    return xml_content
            
            return None
            
        except Exception as e:
            st.error(f"Ошибка подготовки предпросмотра: {str(e)}")
            return None
    
    def _render_export_actions(self, data: Any, export_format: str, options: Dict[str, Any], title: str):
        """Действия по экспорту"""
        st.subheader("📤 Экспорт")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Экспортировать", key="export_button", use_container_width=True):
                self._perform_export(data, export_format, options, title)
        
        with col2:
            if st.button("📋 Копировать в буфер", key="copy_button", use_container_width=True):
                self._copy_to_clipboard(data, export_format, options)
        
        with col3:
            if st.button("📧 Отправить по email", key="email_button", use_container_width=True):
                self._send_via_email(data, export_format, options, title)
    
    def _perform_export(self, data: Any, export_format: str, options: Dict[str, Any], title: str):
        """Выполнение экспорта"""
        try:
            # Подготовка данных
            export_data = self._prepare_export_data(data, export_format, options)
            
            if export_data is None:
                st.error("Не удалось подготовить данные для экспорта")
                return
            
            # Формирование имени файла
            filename = self._generate_filename(options, export_format)
            
            # Создание кнопки скачивания
            if export_format == 'zip':
                # Для ZIP создаем временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    tmp_file.write(export_data)
                    tmp_file_path = tmp_file.name
                
                with open(tmp_file_path, 'rb') as f:
                    st.download_button(
                        label=f"📥 Скачать {self.export_formats[export_format]['name']}",
                        data=f.read(),
                        file_name=filename,
                        mime=self.export_formats[export_format]['mime']
                    )
                
                # Удаляем временный файл
                os.unlink(tmp_file_path)
            else:
                st.download_button(
                    label=f"📥 Скачать {self.export_formats[export_format]['name']}",
                    data=export_data,
                    file_name=filename,
                    mime=self.export_formats[export_format]['mime']
                )
            
            st.success(f"✅ Экспорт в формате {self.export_formats[export_format]['name']} готов")
            
        except Exception as e:
            st.error(f"Ошибка экспорта: {str(e)}")
    
    def _prepare_export_data(self, data: Any, export_format: str, options: Dict[str, Any]) -> Optional[Union[str, bytes]]:
        """Подготовка данных для экспорта"""
        try:
            if export_format == 'csv':
                if isinstance(data, pd.DataFrame):
                    return data.to_csv(
                        sep=options.get('delimiter', ','),
                        index=options.get('include_index', False),
                        encoding=options.get('encoding', 'utf-8')
                    )
                elif isinstance(data, list):
                    df = pd.DataFrame(data)
                    return df.to_csv(
                        sep=options.get('delimiter', ','),
                        index=options.get('include_index', False),
                        encoding=options.get('encoding', 'utf-8')
                    )
            
            elif export_format == 'excel':
                try:
                    if isinstance(data, pd.DataFrame):
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine=options.get('engine', 'openpyxl')) as writer:
                            data.to_excel(
                                writer,
                                sheet_name=options.get('sheet_name', 'Sheet1'),
                                index=options.get('include_index', False),
                                float_format=options.get('float_format', '%.2f')
                            )
                        return buffer.getvalue()
                    elif isinstance(data, list):
                        df = pd.DataFrame(data)
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine=options.get('engine', 'openpyxl')) as writer:
                            df.to_excel(
                                writer,
                                sheet_name=options.get('sheet_name', 'Sheet1'),
                                index=options.get('include_index', False)
                            )
                        return buffer.getvalue()
                except ImportError:
                    st.error("Для экспорта в Excel установите openpyxl: `pip install openpyxl`")
                    return None
            
            elif export_format == 'json':
                if isinstance(data, list):
                    return json.dumps(
                        data,
                        indent=options.get('indent', 2),
                        ensure_ascii=options.get('ensure_ascii', False)
                    )
                elif isinstance(data, dict):
                    return json.dumps(
                        data,
                        indent=options.get('indent', 2),
                        ensure_ascii=options.get('ensure_ascii', False)
                    )
            
            elif export_format == 'txt':
                if isinstance(data, list):
                    lines = []
                    if options.get('include_metadata', True):
                        lines.append(f"Экспорт данных: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        lines.append(f"Количество элементов: {len(data)}")
                        lines.append("-" * 50)
                    
                    for item in data:
                        if options.get('format_type') == 'Структурированный':
                            lines.append(json.dumps(item, ensure_ascii=False, indent=2))
                        else:
                            lines.append(str(item))
                    
                    return '\n'.join(lines)
                elif isinstance(data, str):
                    return data
            
            elif export_format == 'html':
                if isinstance(data, pd.DataFrame):
                    return data.to_html(
                        table_id=options.get('table_id', 'export_table'),
                        classes=options.get('css_class', 'table table-striped'),
                        index=options.get('include_index', False)
                    )
            
            elif export_format == 'xml':
                if isinstance(data, list):
                    root_name = options.get('root_name', 'data')
                    item_name = options.get('item_name', 'item')
                    xml_content = f'<?xml version="1.0" encoding="{options.get("encoding", "utf-8")}"?>\n'
                    xml_content += f'<{root_name}>\n'
                    for item in data:
                        xml_content += f'  <{item_name}>{item}</{item_name}>\n'
                    xml_content += f'</{root_name}>'
                    return xml_content
            
            elif export_format == 'zip':
                return self._create_zip_archive(data, options)
            
            elif export_format == 'yaml':
                return self._create_yaml_export(data, options)
            
            elif export_format == 'markdown':
                return self._create_markdown_export(data, options)
            
            elif export_format == 'tar':
                return self._create_tar_archive(data, options)
            
            elif export_format == 'sql':
                return self._create_sql_export(data, options)
            
            return None
            
        except Exception as e:
            st.error(f"Ошибка подготовки данных: {str(e)}")
            return None
    
    def _create_zip_archive(self, data: Any, options: Dict[str, Any]) -> bytes:
        """Создание ZIP архива"""
        buffer = BytesIO()
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Добавляем основные данные
            if isinstance(data, list):
                # Экспортируем в несколько форматов
                formats_to_include = ['csv', 'json', 'txt']
                
                for fmt in formats_to_include:
                    try:
                        if fmt == 'csv':
                            df = pd.DataFrame(data)
                            csv_data = df.to_csv(index=False)
                            zip_file.writestr(f"data.{fmt}", csv_data)
                        elif fmt == 'json':
                            json_data = json.dumps(data, indent=2, ensure_ascii=False)
                            zip_file.writestr(f"data.{fmt}", json_data)
                        elif fmt == 'txt':
                            txt_data = '\n'.join([str(item) for item in data])
                            zip_file.writestr(f"data.{fmt}", txt_data)
                    except:
                        continue
            
            # Добавляем метаданные
            if options.get('include_metadata', True):
                metadata = {
                    'export_time': datetime.now().isoformat(),
                    'data_type': type(data).__name__,
                    'data_size': len(data) if isinstance(data, (list, dict)) else 1,
                    'export_options': options
                }
                
                metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                zip_file.writestr("metadata.json", metadata_json)
            
            # Добавляем комментарий
            if options.get('comment'):
                zip_file.comment = options['comment'].encode('utf-8')
        
        return buffer.getvalue()
    
    def _generate_filename(self, options: Dict[str, Any], export_format: str) -> str:
        """Генерация имени файла"""
        base_name = options.get('filename', 'export')
        
        if options.get('include_timestamp', True):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = f"{base_name}_{timestamp}"
        
        extension = self.export_formats[export_format]['extension']
        return f"{base_name}{extension}"
    
    def _copy_to_clipboard(self, data: Any, export_format: str, options: Dict[str, Any]):
        """Копирование в буфер обмена"""
        try:
            export_data = self._prepare_export_data(data, export_format, options)
            
            if export_data:
                if isinstance(export_data, bytes):
                    export_data = export_data.decode('utf-8')
                
                # В Streamlit используем session_state для имитации буфера
                st.session_state['clipboard_data'] = export_data
                st.success("✅ Данные скопированы в буфер обмена")
                
                # Показываем кнопку для просмотра скопированных данных
                if st.button("📋 Показать скопированные данные"):
                    st.text_area("Скопированные данные:", value=export_data, height=200)
            else:
                st.error("Не удалось подготовить данные для копирования")
                
        except Exception as e:
            st.error(f"Ошибка копирования: {str(e)}")
    
    def _send_via_email(self, data: Any, export_format: str, options: Dict[str, Any], title: str):
        """Отправка по email"""
        st.info("📧 Функция отправки по email будет доступна в следующем обновлении")
        
        # Заглушка для будущей функциональности
        with st.expander("Настройки email", expanded=False):
            st.text_input("Email получателя", key="email_recipient")
            st.text_input("Тема письма", value=f"Экспорт: {title}", key="email_subject")
            st.text_area("Текст письма", key="email_body")
            st.button("Отправить", disabled=True)
    
    def _render_additional_options(self, data: Any, data_type: str):
        """Дополнительные опции экспорта"""
        st.subheader("🔧 Дополнительные опции")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Планирование экспорта
            schedule_export = st.checkbox("Запланировать регулярный экспорт", key="schedule_export")
            if schedule_export:
                st.selectbox("Частота", ["Ежедневно", "Еженедельно", "Ежемесячно"], key="export_frequency")
                st.time_input("Время экспорта", key="export_time")
        
        with col2:
            # Уведомления
            enable_notifications = st.checkbox("Включить уведомления", key="enable_notifications")
            if enable_notifications:
                st.checkbox("Email уведомления", key="email_notifications")
                st.checkbox("Push уведомления", key="push_notifications")
        
        # Автоматизация
        st.write("**Автоматизация:**")
        auto_export = st.checkbox("Автоматический экспорт при изменении данных", key="auto_export")
        if auto_export:
            st.selectbox("Формат по умолчанию", list(self.export_formats.keys()), 
                        format_func=lambda x: self.export_formats[x]['name'])
            st.text_input("Папка назначения", key="export_folder")
    
    def _get_yaml_options(self) -> Dict[str, Any]:
        """Опции для YAML экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            indent = st.slider("Отступ", 2, 8, 2, key="yaml_indent")
            default_flow_style = st.checkbox("Использовать flow style", value=False, key="yaml_flow")
        
        with col2:
            allow_unicode = st.checkbox("Разрешить Unicode", value=True, key="yaml_unicode")
            sort_keys = st.checkbox("Сортировать ключи", value=False, key="yaml_sort")
        
        return {
            'indent': indent,
            'default_flow_style': default_flow_style,
            'allow_unicode': allow_unicode,
            'sort_keys': sort_keys
        }
    
    def _get_markdown_options(self) -> Dict[str, Any]:
        """Опции для Markdown экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            include_metadata = st.checkbox("Включить метаданные", value=True, key="md_metadata")
            table_format = st.selectbox("Формат таблиц", ["GitHub", "Grid", "Simple"], key="md_table_format")
        
        with col2:
            include_toc = st.checkbox("Включить оглавление", value=False, key="md_toc")
            header_level = st.selectbox("Уровень заголовков", [1, 2, 3, 4, 5, 6], index=1, key="md_header_level")
        
        return {
            'include_metadata': include_metadata,
            'table_format': table_format,
            'include_toc': include_toc,
            'header_level': header_level
        }
    
    def _get_tar_options(self) -> Dict[str, Any]:
        """Опции для TAR экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            compression = st.selectbox("Сжатие", ["Нет", "Gzip", "Bzip2"], key="tar_compression")
            include_metadata = st.checkbox("Включить метаданные", value=True, key="tar_metadata")
        
        with col2:
            comment = st.text_input("Комментарий к архиву", key="tar_comment")
            preserve_permissions = st.checkbox("Сохранить права доступа", value=False, key="tar_permissions")
        
        return {
            'compression': compression,
            'include_metadata': include_metadata,
            'comment': comment,
            'preserve_permissions': preserve_permissions
        }
    
    def _get_sql_options(self) -> Dict[str, Any]:
        """Опции для SQL экспорта"""
        col1, col2 = st.columns(2)
        
        with col1:
            table_name = st.text_input("Имя таблицы", value="exported_data", key="sql_table_name")
            include_create = st.checkbox("Включить CREATE TABLE", value=True, key="sql_create")
        
        with col2:
            include_drop = st.checkbox("Включить DROP TABLE", value=False, key="sql_drop")
            batch_size = st.number_input("Размер пакета", min_value=1, max_value=1000, value=100, key="sql_batch_size")
        
        return {
            'table_name': table_name,
            'include_create': include_create,
            'include_drop': include_drop,
            'batch_size': batch_size
        }
    
    def _create_yaml_export(self, data: Any, options: Dict[str, Any]) -> str:
        """Создание YAML экспорта"""
        try:
            import yaml
            
            if isinstance(data, list):
                yaml_data = data
            elif isinstance(data, dict):
                yaml_data = data
            elif isinstance(data, pd.DataFrame):
                yaml_data = data.to_dict('records')
            else:
                yaml_data = {'data': data}
            
            return yaml.dump(
                yaml_data,
                default_flow_style=options.get('default_flow_style', False),
                allow_unicode=options.get('allow_unicode', True),
                sort_keys=options.get('sort_keys', False),
                indent=options.get('indent', 2)
            )
        except ImportError:
            st.error("Для экспорта в YAML установите PyYAML: `pip install PyYAML`")
            return None
        except Exception as e:
            st.error(f"Ошибка создания YAML: {str(e)}")
            return None
    
    def _create_markdown_export(self, data: Any, options: Dict[str, Any]) -> str:
        """Создание Markdown экспорта"""
        try:
            md_content = []
            
            # Заголовок
            header_level = options.get('header_level', 2)
            md_content.append(f"{'#' * header_level} Экспорт данных")
            md_content.append("")
            
            # Метаданные
            if options.get('include_metadata', True):
                md_content.append("## Метаданные")
                md_content.append(f"- **Дата экспорта:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                md_content.append(f"- **Тип данных:** {type(data).__name__}")
                if isinstance(data, (list, dict)):
                    md_content.append(f"- **Количество элементов:** {len(data)}")
                md_content.append("")
            
            # Оглавление
            if options.get('include_toc', False):
                md_content.append("## Оглавление")
                md_content.append("- [Данные](#данные)")
                md_content.append("")
            
            # Основные данные
            md_content.append("## Данные")
            md_content.append("")
            
            if isinstance(data, pd.DataFrame):
                # Таблица в Markdown
                table_format = options.get('table_format', 'GitHub')
                if table_format == 'GitHub':
                    md_content.append(data.to_markdown(index=False))
                else:
                    # Простая таблица
                    md_content.append("| " + " | ".join(data.columns) + " |")
                    md_content.append("| " + " | ".join(["---"] * len(data.columns)) + " |")
                    for _, row in data.iterrows():
                        md_content.append("| " + " | ".join(str(cell) for cell in row) + " |")
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    md_content.append(f"### Элемент {i+1}")
                    if isinstance(item, dict):
                        for key, value in item.items():
                            md_content.append(f"- **{key}:** {value}")
                    else:
                        md_content.append(f"{item}")
                    md_content.append("")
            
            elif isinstance(data, dict):
                for key, value in data.items():
                    md_content.append(f"### {key}")
                    if isinstance(value, (list, dict)):
                        md_content.append(f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```")
                    else:
                        md_content.append(f"{value}")
                    md_content.append("")
            
            else:
                md_content.append(f"```\n{str(data)}\n```")
            
            return "\n".join(md_content)
            
        except Exception as e:
            st.error(f"Ошибка создания Markdown: {str(e)}")
            return None
    
    def _create_tar_archive(self, data: Any, options: Dict[str, Any]) -> bytes:
        """Создание TAR архива"""
        try:
            import tarfile
            
            buffer = BytesIO()
            
            # Определяем режим сжатия
            compression = options.get('compression', 'Нет')
            if compression == 'Gzip':
                mode = 'w:gz'
            elif compression == 'Bzip2':
                mode = 'w:bz2'
            else:
                mode = 'w'
            
            with tarfile.open(fileobj=buffer, mode=mode) as tar:
                # Добавляем основные данные
                if isinstance(data, list):
                    # Экспортируем в несколько форматов
                    formats_to_include = ['csv', 'json', 'txt']
                    
                    for fmt in formats_to_include:
                        try:
                            if fmt == 'csv':
                                df = pd.DataFrame(data)
                                csv_data = df.to_csv(index=False)
                                tarinfo = tarfile.TarInfo(name=f"data.{fmt}")
                                tarinfo.size = len(csv_data.encode('utf-8'))
                                tar.addfile(tarinfo, BytesIO(csv_data.encode('utf-8')))
                            elif fmt == 'json':
                                json_data = json.dumps(data, indent=2, ensure_ascii=False)
                                tarinfo = tarfile.TarInfo(name=f"data.{fmt}")
                                tarinfo.size = len(json_data.encode('utf-8'))
                                tar.addfile(tarinfo, BytesIO(json_data.encode('utf-8')))
                            elif fmt == 'txt':
                                txt_data = '\n'.join([str(item) for item in data])
                                tarinfo = tarfile.TarInfo(name=f"data.{fmt}")
                                tarinfo.size = len(txt_data.encode('utf-8'))
                                tar.addfile(tarinfo, BytesIO(txt_data.encode('utf-8')))
                        except:
                            continue
                
                # Добавляем метаданные
                if options.get('include_metadata', True):
                    metadata = {
                        'export_time': datetime.now().isoformat(),
                        'data_type': type(data).__name__,
                        'data_size': len(data) if isinstance(data, (list, dict)) else 1,
                        'export_options': options
                    }
                    
                    metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                    tarinfo = tarfile.TarInfo(name="metadata.json")
                    tarinfo.size = len(metadata_json.encode('utf-8'))
                    tar.addfile(tarinfo, BytesIO(metadata_json.encode('utf-8')))
            
            return buffer.getvalue()
            
        except Exception as e:
            st.error(f"Ошибка создания TAR архива: {str(e)}")
            return None
    
    def _create_sql_export(self, data: Any, options: Dict[str, Any]) -> str:
        """Создание SQL экспорта"""
        try:
            sql_content = []
            
            table_name = options.get('table_name', 'exported_data')
            include_drop = options.get('include_drop', False)
            include_create = options.get('include_create', True)
            batch_size = options.get('batch_size', 100)
            
            # DROP TABLE
            if include_drop:
                sql_content.append(f"DROP TABLE IF EXISTS `{table_name}`;")
                sql_content.append("")
            
            if isinstance(data, pd.DataFrame):
                # CREATE TABLE
                if include_create:
                    sql_content.append(f"CREATE TABLE `{table_name}` (")
                    
                    columns = []
                    for col in data.columns:
                        # Определяем тип столбца
                        dtype = str(data[col].dtype)
                        if 'int' in dtype:
                            sql_type = 'INT'
                        elif 'float' in dtype:
                            sql_type = 'FLOAT'
                        elif 'bool' in dtype:
                            sql_type = 'BOOLEAN'
                        else:
                            sql_type = 'TEXT'
                        
                        columns.append(f"  `{col}` {sql_type}")
                    
                    sql_content.append(",\n".join(columns))
                    sql_content.append(");")
                    sql_content.append("")
                
                # INSERT statements
                for i in range(0, len(data), batch_size):
                    batch = data.iloc[i:i+batch_size]
                    
                    sql_content.append(f"INSERT INTO `{table_name}` VALUES")
                    
                    values = []
                    for _, row in batch.iterrows():
                        row_values = []
                        for value in row:
                            if pd.isna(value):
                                row_values.append('NULL')
                            elif isinstance(value, str):
                                # Экранируем кавычки
                                escaped_value = value.replace("'", "''")
                                row_values.append(f"'{escaped_value}'")
                            else:
                                row_values.append(str(value))
                        
                        values.append(f"({', '.join(row_values)})")
                    
                    sql_content.append(",\n".join(values) + ";")
                    sql_content.append("")
            
            elif isinstance(data, list):
                # Простой экспорт списка
                sql_content.append(f"CREATE TABLE `{table_name}` (")
                sql_content.append("  `id` INT AUTO_INCREMENT PRIMARY KEY,")
                sql_content.append("  `value` TEXT")
                sql_content.append(");")
                sql_content.append("")
                
                for i, item in enumerate(data):
                    escaped_value = str(item).replace("'", "''")
                    sql_content.append(f"INSERT INTO `{table_name}` (`value`) VALUES ('{escaped_value}');")
            
            return "\n".join(sql_content)
            
        except Exception as e:
            st.error(f"Ошибка создания SQL: {str(e)}")
            return None
