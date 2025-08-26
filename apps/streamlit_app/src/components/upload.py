"""
Компонент загрузки документов
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
import os
from datetime import datetime


class DocumentUploader:
    """Компонент для загрузки документов"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
        
        # Поддерживаемые форматы
        self.supported_formats = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'html': 'text/html',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'tiff': 'image/tiff',
            'eml': 'message/rfc822'
        }
    
    def render(self):
        """Отображение интерфейса загрузки"""
        st.header("📤 Загрузка документов")
        
        # Информация о поддерживаемых форматах
        with st.expander("📋 Поддерживаемые форматы"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Документы:**")
                st.write("- PDF (векторный и сканированный)")
                st.write("- DOCX (Word документы)")
                st.write("- XLSX (Excel таблицы)")
                st.write("- HTML (веб-страницы)")
                st.write("- TXT (текстовые файлы)")
                st.write("- EML (электронные письма)")
            
            with col2:
                st.write("**Изображения:**")
                st.write("- JPG/JPEG")
                st.write("- PNG")
                st.write("- TIFF")
                st.write("")
                st.write("**Ограничения:**")
                st.write("- Максимальный размер: 100 MB")
                st.write("- Автоматический OCR для изображений")
                st.write("- Извлечение таблиц из PDF")
        
        # Форма загрузки
        with st.form("upload_form", clear_on_submit=True):
            # Выбор файла
            uploaded_file = st.file_uploader(
                "Выберите файл для загрузки",
                type=list(self.supported_formats.keys()),
                help="Поддерживаются PDF, DOCX, XLSX, HTML, TXT, изображения"
            )
            
            # Метаданные документа
            st.subheader("📝 Метаданные документа")
            
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input(
                    "Название документа",
                    placeholder="Введите название документа",
                    help="Краткое описание содержимого"
                )
                
                description = st.text_area(
                    "Описание",
                    placeholder="Подробное описание документа",
                    help="Дополнительная информация о содержимом",
                    max_chars=500
                )
            
            with col2:
                tags = st.multiselect(
                    "Теги",
                    ["важное", "контракт", "отчет", "анализ", "финансы", "юридический", "технический"],
                    help="Выберите или введите теги для категоризации"
                )
                
                custom_tags = st.text_input(
                    "Дополнительные теги",
                    placeholder="Введите через запятую",
                    help="Добавьте свои теги"
                )
                
                if custom_tags:
                    custom_tag_list = [tag.strip() for tag in custom_tags.split(",") if tag.strip()]
                    tags.extend(custom_tag_list)
            
            # Настройки обработки
            st.subheader("⚙️ Настройки обработки")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chunk_size = st.selectbox(
                    "Размер чанков",
                    [500, 1000, 1500, 2000],
                    index=1,
                    help="Размер фрагментов для разбиения документа"
                )
                
                chunk_overlap = st.selectbox(
                    "Перекрытие чанков",
                    [100, 200, 300, 400],
                    index=1,
                    help="Перекрытие между соседними фрагментами"
                )
            
            with col2:
                enable_ocr = st.checkbox(
                    "Включить OCR",
                    value=True,
                    help="Оптическое распознавание текста для изображений"
                )
                
                extract_tables = st.checkbox(
                    "Извлекать таблицы",
                    value=True,
                    help="Автоматическое извлечение таблиц"
                )
            
            with col3:
                language = st.selectbox(
                    "Язык документа",
                    ["auto", "ru", "en", "de", "fr"],
                    format_func=lambda x: {
                        "auto": "Автоопределение",
                        "ru": "Русский",
                        "en": "Английский",
                        "de": "Немецкий",
                        "fr": "Французский"
                    }[x]
                )
                
                priority = st.selectbox(
                    "Приоритет обработки",
                    ["low", "normal", "high"],
                    index=1,
                    format_func=lambda x: {
                        "low": "Низкий",
                        "normal": "Обычный",
                        "high": "Высокий"
                    }[x]
                )
            
            # Дополнительные опции
            with st.expander("🔧 Дополнительные опции"):
                col1, col2 = st.columns(2)
                
                with col1:
                    auto_rotate = st.checkbox(
                        "Автоповорот страниц",
                        value=True,
                        help="Автоматическое определение ориентации"
                    )
                    
                    deskew = st.checkbox(
                        "Выравнивание текста",
                        value=True,
                        help="Исправление наклона текста"
                    )
                
                with col2:
                    preserve_formatting = st.checkbox(
                        "Сохранить форматирование",
                        value=True,
                        help="Сохранить исходное форматирование"
                    )
                    
                    generate_summary = st.checkbox(
                        "Генерировать краткое содержание",
                        value=False,
                        help="Автоматическое создание аннотации"
                    )
            
            # Кнопка загрузки
            submitted = st.form_submit_button("📤 Загрузить документ", use_container_width=True)
        
        # Обработка загрузки
        if submitted and uploaded_file:
            self._upload_document(
                file=uploaded_file,
                title=title or uploaded_file.name,
                description=description,
                tags=tags,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enable_ocr=enable_ocr,
                extract_tables=extract_tables,
                language=language,
                priority=priority,
                auto_rotate=auto_rotate,
                deskew=deskew,
                preserve_formatting=preserve_formatting,
                generate_summary=generate_summary
            )
        
        # История загрузок
        self._render_upload_history()
    
    def _upload_document(self, **kwargs):
        """Загрузка документа"""
        try:
            with st.spinner("📤 Загружается документ..."):
                # Подготавливаем файл
                file = kwargs["file"]
                
                # Проверяем размер файла
                file.seek(0, 2)  # Перемещаемся в конец файла
                file_size = file.tell()
                file.seek(0)  # Возвращаемся в начало
                
                max_size = 100 * 1024 * 1024  # 100 MB
                if file_size > max_size:
                    st.error(f"❌ Файл слишком большой: {file_size / (1024*1024):.1f} MB. Максимум: 100 MB")
                    return
                
                # Формируем данные для загрузки
                files = {"file": file}
                
                data = {
                    "title": kwargs["title"],
                    "description": kwargs["description"],
                    "tags": ",".join(kwargs["tags"]) if kwargs["tags"] else "",
                    "chunk_size": kwargs["chunk_size"],
                    "chunk_overlap": kwargs["chunk_overlap"],
                    "enable_ocr": kwargs["enable_ocr"],
                    "extract_tables": kwargs["extract_tables"],
                    "language": kwargs["language"],
                    "priority": kwargs["priority"],
                    "auto_rotate": kwargs["auto_rotate"],
                    "deskew": kwargs["deskew"],
                    "preserve_formatting": kwargs["preserve_formatting"],
                    "generate_summary": kwargs["generate_summary"]
                }
                
                # Убираем пустые значения
                data = {k: v for k, v in data.items() if v is not None and v != ""}
                
                # Выполняем загрузку
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                response = requests.post(
                    f"{self.api_base_url}/api/v1/documents/upload",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Документ успешно загружен!")
                    
                    # Показываем информацию о загруженном файле
                    self._show_upload_result(result, kwargs)
                    
                    # Сохраняем в историю загрузок
                    self._save_upload_history(result, kwargs)
                    
                else:
                    error_msg = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка загрузки: {error_msg}")
                    
        except requests.exceptions.Timeout:
            st.error("⏱️ Превышено время ожидания загрузки.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Ошибка соединения с API.")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
    
    def _show_upload_result(self, result: Dict[str, Any], upload_params: Dict[str, Any]):
        """Отображение результата загрузки"""
        st.subheader("📋 Информация о загруженном документе")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**ID документа:** {result.get('document_id', 'N/A')}")
            st.write(f"**Название:** {result.get('title', upload_params['title'])}")
            st.write(f"**Имя файла:** {result.get('filename', 'N/A')}")
            st.write(f"**MIME тип:** {result.get('mime_type', 'N/A')}")
        
        with col2:
            st.write(f"**Размер:** {result.get('size', 'N/A')} байт")
            st.write(f"**SHA256:** {result.get('sha256', 'N/A')[:16]}...")
            st.write(f"**Статус:** {result.get('status', 'N/A')}")
            st.write(f"**Дата загрузки:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Параметры обработки
        st.subheader("⚙️ Параметры обработки")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Размер чанков:** {upload_params['chunk_size']}")
            st.write(f"**Перекрытие:** {upload_params['chunk_overlap']}")
            st.write(f"**OCR:** {'Включен' if upload_params['enable_ocr'] else 'Отключен'}")
            st.write(f"**Извлечение таблиц:** {'Включено' if upload_params['extract_tables'] else 'Отключено'}")
        
        with col2:
            st.write(f"**Язык:** {upload_params['language']}")
            st.write(f"**Приоритет:** {upload_params['priority']}")
            st.write(f"**Автоповорот:** {'Включен' if upload_params['auto_rotate'] else 'Отключен'}")
            st.write(f"**Выравнивание:** {'Включено' if upload_params['deskew'] else 'Отключено'}")
        
        # Следующие шаги
        st.info("📝 Документ будет обработан в фоновом режиме. Вы можете отслеживать статус в разделе 'Документы'.")
        
        # Кнопки действий
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 Перейти к документам", key="go_to_docs"):
                st.switch_page("📚 Документы")
        
        with col2:
            if st.button("🔍 Начать поиск", key="start_search"):
                st.switch_page("🔍 Поиск")
        
        with col3:
            if st.button("💬 Открыть чат", key="open_chat"):
                st.switch_page("💬 Чат")
    
    def _save_upload_history(self, result: Dict[str, Any], upload_params: Dict[str, Any]):
        """Сохранение в историю загрузок"""
        if "upload_history" not in st.session_state:
            st.session_state.upload_history = []
        
        upload_record = {
            "timestamp": datetime.now(),
            "document_id": result.get('document_id'),
            "filename": result.get('filename'),
            "title": upload_params['title'],
            "size": result.get('size'),
            "status": result.get('status'),
            "parameters": upload_params
        }
        
        st.session_state.upload_history.append(upload_record)
    
    def _render_upload_history(self):
        """Отображение истории загрузок"""
        if "upload_history" not in st.session_state or not st.session_state.upload_history:
            return
        
        st.subheader("📚 История загрузок")
        
        # Фильтры
        with st.expander("🔍 Фильтры истории"):
            col1, col2 = st.columns(2)
            
            with col1:
                show_successful = st.checkbox("Успешные загрузки", value=True)
                show_failed = st.checkbox("Неудачные загрузки", value=True)
            
            with col2:
                date_filter = st.date_input(
                    "Фильтр по дате",
                    value=None
                )
        
        # Отображение истории
        history = st.session_state.upload_history
        
        # Применяем фильтры
        if date_filter:
            history = [h for h in history if h["timestamp"].date() == date_filter]
        
        if not show_successful:
            history = [h for h in history if h["status"] != "uploaded"]
        
        if not show_failed:
            history = [h for h in history if h["status"] == "uploaded"]
        
        if not history:
            st.info("Нет загрузок, соответствующих фильтрам")
            return
        
        # Отображаем историю
        for i, record in enumerate(reversed(history[-10:])):  # Последние 10 загрузок
            with st.expander(f"📄 {record['title']} ({record['timestamp'].strftime('%H:%M:%S')})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {record['document_id']}")
                    st.write(f"**Файл:** {record['filename']}")
                    st.write(f"**Размер:** {record['size']} байт")
                
                with col2:
                    status_icon = "✅" if record['status'] == 'uploaded' else "❌"
                    st.write(f"**Статус:** {status_icon} {record['status']}")
                    st.write(f"**Дата:** {record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Параметры обработки
                if record.get('parameters'):
                    with st.expander("⚙️ Параметры обработки"):
                        params = record['parameters']
                        st.write(f"**Размер чанков:** {params.get('chunk_size', 'N/A')}")
                        st.write(f"**OCR:** {params.get('enable_ocr', 'N/A')}")
                        st.write(f"**Извлечение таблиц:** {params.get('extract_tables', 'N/A')}")
                
                # Действия
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"👁️ Просмотр", key=f"view_history_{i}"):
                        st.info("Функция просмотра в разработке")
                
                with col2:
                    if st.button(f"🔍 Статус", key=f"status_{i}"):
                        st.info("Функция проверки статуса в разработке")
                
                with col3:
                    if st.button(f"🗑️ Удалить", key=f"delete_history_{i}"):
                        # Удаляем из истории
                        st.session_state.upload_history.pop(-(i+1))
                        st.success("✅ Запись удалена из истории")
                        st.rerun()
        
        # Очистка истории
        if st.button("🗑️ Очистить всю историю"):
            st.session_state.upload_history = []
            st.success("✅ История загрузок очищена")
            st.rerun()
