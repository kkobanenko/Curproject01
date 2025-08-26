"""
Компонент поиска документов
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


class SearchForm:
    """Форма поиска документов"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
    
    def render(self) -> Optional[Dict[str, Any]]:
        """Отображение формы поиска"""
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
                top_k = st.number_input(
                    "Количество результатов", 
                    min_value=1, 
                    max_value=100, 
                    value=20
                )
            
            # Дополнительные параметры поиска
            with st.expander("🔧 Дополнительные параметры"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    search_type = st.selectbox(
                        "Тип поиска",
                        ["semantic", "keyword", "hybrid"],
                        format_func=lambda x: {
                            "semantic": "Семантический",
                            "keyword": "Ключевые слова", 
                            "hybrid": "Гибридный"
                        }[x]
                    )
                
                with col2:
                    min_score = st.slider(
                        "Минимальная релевантность",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.3,
                        step=0.1
                    )
                
                with col3:
                    include_tables = st.checkbox("Включать таблицы", value=True)
                    include_images = st.checkbox("Включать изображения", value=False)
            
            # Фильтры по метаданным
            with st.expander("📋 Фильтры"):
                col1, col2 = st.columns(2)
                
                with col1:
                    file_types = st.multiselect(
                        "Типы файлов",
                        ["PDF", "DOCX", "XLSX", "HTML", "TXT"],
                        default=["PDF", "DOCX"]
                    )
                    
                    date_from = st.date_input(
                        "Дата загрузки с",
                        value=None
                    )
                
                with col2:
                    tags = st.multiselect(
                        "Теги",
                        ["важное", "контракт", "отчет", "анализ"],
                        default=[]
                    )
                    
                    date_to = st.date_input(
                        "Дата загрузки по",
                        value=None
                    )
            
            submitted = st.form_submit_button("🔍 Найти", use_container_width=True)
        
        if submitted and query:
            return self._perform_search(
                query=query,
                top_k=top_k,
                search_type=search_type,
                min_score=min_score,
                include_tables=include_tables,
                include_images=include_images,
                file_types=file_types,
                tags=tags,
                date_from=date_from,
                date_to=date_to
            )
        
        return None
    
    def _perform_search(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Выполнение поиска"""
        try:
            with st.spinner("Выполняется поиск..."):
                # Формируем параметры поиска
                search_params = {
                    "query": kwargs["query"],
                    "top_k": kwargs["top_k"],
                    "search_type": kwargs["search_type"],
                    "min_score": kwargs["min_score"],
                    "include_tables": kwargs["include_tables"],
                    "include_images": kwargs["include_images"]
                }
                
                # Добавляем фильтры если указаны
                filters = {}
                if kwargs["file_types"]:
                    filters["mime_types"] = kwargs["file_types"]
                if kwargs["tags"]:
                    filters["tags"] = kwargs["tags"]
                if kwargs["date_from"]:
                    filters["date_from"] = kwargs["date_from"].isoformat()
                if kwargs["date_to"]:
                    filters["date_to"] = kwargs["date_to"].isoformat()
                
                if filters:
                    search_params["filters"] = filters
                
                # Выполняем поиск
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                response = requests.post(
                    f"{self.api_base_url}/api/v1/search",
                    json=search_params,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = response.json().get("detail", "Неизвестная ошибка")
                    st.error(f"❌ Ошибка поиска: {error_msg}")
                    return None
                    
        except requests.exceptions.Timeout:
            st.error("⏱️ Превышено время ожидания поиска.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Ошибка соединения с API.")
            return None
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
            return None


class SearchResults:
    """Отображение результатов поиска"""
    
    def __init__(self, results: Dict[str, Any]):
        self.results = results
    
    def render(self):
        """Отображение результатов поиска"""
        if not self.results:
            st.info("Нет результатов для отображения")
            return
        
        # Статистика поиска
        total_results = self.results.get('total_results', len(self.results.get('results', [])))
        search_time = self.results.get('search_time', 0)
        
        st.success(f"✅ Найдено {total_results} результатов за {search_time:.3f} сек")
        
        # Фильтры результатов
        with st.expander("🔍 Фильтры результатов"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sort_by = st.selectbox(
                    "Сортировка",
                    ["relevance", "date", "size"],
                    format_func=lambda x: {
                        "relevance": "По релевантности",
                        "date": "По дате",
                        "size": "По размеру"
                    }[x]
                )
            
            with col2:
                min_score_filter = st.slider(
                    "Минимальная релевантность",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.1
                )
            
            with col3:
                result_types = st.multiselect(
                    "Типы результатов",
                    ["text", "table", "image"],
                    default=["text", "table"]
                )
        
        # Отображение результатов
        results_list = self.results.get('results', [])
        
        if not results_list:
            st.info("Нет результатов, соответствующих фильтрам")
            return
        
        # Применяем фильтры
        filtered_results = self._filter_results(results_list, min_score_filter, result_types)
        
        if not filtered_results:
            st.info("Нет результатов, соответствующих фильтрам")
            return
        
        # Отображаем результаты
        for i, result in enumerate(filtered_results):
            self._render_result(result, i + 1)
        
        # Пагинация если нужно
        if len(filtered_results) < total_results:
            st.info(f"Показано {len(filtered_results)} из {total_results} результатов")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                if st.button("📄 Показать еще"):
                    st.info("Функция пагинации в разработке")
    
    def _filter_results(self, results: List[Dict], min_score: float, types: List[str]) -> List[Dict]:
        """Фильтрация результатов"""
        filtered = []
        
        for result in results:
            # Фильтр по релевантности
            if result.get('score', 0) < min_score:
                continue
            
            # Фильтр по типу
            result_type = result.get('kind', 'text')
            if types and result_type not in types:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _render_result(self, result: Dict[str, Any], index: int):
        """Отображение отдельного результата"""
        score = result.get('score', 0)
        result_type = result.get('kind', 'text')
        
        # Определяем цвет и иконку по типу
        if result_type == 'table':
            icon = "📊"
            color = "blue"
        elif result_type == 'image':
            icon = "🖼️"
            color = "green"
        else:
            icon = "📄"
            color = "gray"
        
        # Заголовок результата
        with st.expander(f"{icon} Результат {index} (релевантность: {score:.3f})"):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Метаданные
                st.write(f"**Тип:** {result_type}")
                st.write(f"**Страница:** {result.get('page_no', 'N/A')}")
                st.write(f"**Документ:** {result.get('document_title', 'N/A')}")
                
                # Дополнительная информация
                if result.get('chunk_id'):
                    st.write(f"**Чанк ID:** {result['chunk_id']}")
                
                if result.get('tags'):
                    st.write("**Теги:**")
                    for tag in result['tags']:
                        st.write(f"- {tag}")
            
            with col2:
                # Содержимое
                if result_type == 'table':
                    st.write("**Таблица:**")
                    if result.get('table_html'):
                        st.html(result['table_html'])
                    elif result.get('table_data'):
                        st.dataframe(result['table_data'])
                    else:
                        st.write("Данные таблицы недоступны")
                
                elif result_type == 'image':
                    st.write("**Изображение:**")
                    if result.get('image_url'):
                        st.image(result['image_url'])
                    else:
                        st.write("Изображение недоступно")
                
                else:
                    # Текстовый результат
                    st.write("**Текст:**")
                    content = result.get('content', '')
                    
                    if len(content) > 1000:
                        # Показываем первые 500 и последние 500 символов
                        st.write(content[:500] + "...")
                        with st.expander("Показать полный текст"):
                            st.write(content)
                        st.write("..." + content[-500:])
                    else:
                        st.write(content)
                
                # Цитаты и источники
                if result.get('citations'):
                    st.write("**Источники:**")
                    for citation in result['citations']:
                        st.write(f"- {citation.get('source', 'N/A')} (стр. {citation.get('page', 'N/A')})")
                
                # Действия с результатом
                st.divider()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"👁️ Просмотр", key=f"view_{index}"):
                        st.info("Функция просмотра в разработке")
                
                with col2:
                    if st.button(f"💬 Чат", key=f"chat_{index}"):
                        st.info("Функция чата в разработке")
                
                with col3:
                    if st.button(f"📋 Копировать", key=f"copy_{index}"):
                        st.success("✅ Скопировано в буфер обмена")
                        st.session_state.copied_content = content
