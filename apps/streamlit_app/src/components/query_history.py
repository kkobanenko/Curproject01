"""
Компонент для истории запросов
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime, timedelta
import json
from io import BytesIO


class QueryHistory:
    """Компонент для отображения и управления историей запросов"""
    
    def __init__(self, api_base_url: str, access_token: str = None):
        self.api_base_url = api_base_url
        self.access_token = access_token
        self.history_types = {
            'search': '🔍 Поиск',
            'chat': '💬 Чат',
            'upload': '📤 Загрузка',
            'download': '📥 Скачивание',
            'analysis': '📊 Анализ',
            'preview': '👁️ Предпросмотр',
            'export': '💾 Экспорт',
            'settings': '⚙️ Настройки'
        }
    
    def render(self):
        """Основной метод рендеринга истории запросов"""
        st.header("📚 История запросов")
        
        # Фильтры и настройки
        filters = self._render_filters()
        
        # Получение истории
        history_data = self._get_query_history(filters)
        
        if history_data:
            # Отображение статистики
            self._render_statistics(history_data)
            
            # Отображение истории
            self._render_history_list(history_data, filters)
            
            # Быстрый доступ к частым запросам
            self._render_quick_access(history_data)
            
            # Действия с историей
            self._render_history_actions(history_data)
        else:
            st.info("📭 История запросов пуста")
    
    def _render_filters(self) -> Dict[str, Any]:
        """Рендеринг фильтров для истории"""
        st.subheader("🔍 Фильтры")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Тип запроса
            selected_types = st.multiselect(
                "Тип запроса",
                list(self.history_types.values()),
                default=list(self.history_types.values()),
                key="history_type_filter"
            )
            
            # Преобразование обратно в ключи
            type_keys = [k for k, v in self.history_types.items() if v in selected_types]
        
        with col2:
            # Временной диапазон
            time_range = st.selectbox(
                "Временной диапазон",
                [
                    "Последний час",
                    "Последние 24 часа", 
                    "Последние 7 дней",
                    "Последние 30 дней",
                    "Все время",
                    "Произвольный"
                ],
                key="time_range_filter"
            )
            
            if time_range == "Произвольный":
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    start_date = st.date_input("С даты", key="start_date_filter")
                with col2_2:
                    end_date = st.date_input("По дату", key="end_date_filter")
            else:
                start_date = None
                end_date = None
        
        with col3:
            # Статус запроса
            status_filter = st.multiselect(
                "Статус",
                ["Успешно", "Ошибка", "В процессе"],
                default=["Успешно", "Ошибка", "В процессе"],
                key="status_filter"
            )
            
            # Сортировка
            sort_by = st.selectbox(
                "Сортировка",
                ["По дате (новые)", "По дате (старые)", "По типу", "По статусу"],
                key="sort_filter"
            )
        
        # Поиск по тексту
        search_text = st.text_input(
            "🔍 Поиск в истории",
            placeholder="Введите текст для поиска в запросах...",
            key="history_search_text"
        )
        
        return {
            'types': type_keys,
            'time_range': time_range,
            'start_date': start_date,
            'end_date': end_date,
            'status': status_filter,
            'sort_by': sort_by,
            'search_text': search_text
        }
    
    def _get_query_history(self, filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Получение истории запросов из API"""
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            # Формирование параметров запроса
            params = {
                'types': ','.join(filters['types']),
                'status': ','.join(filters['status']),
                'sort_by': filters['sort_by'],
                'limit': 100  # Ограничиваем количество записей
            }
            
            if filters['search_text']:
                params['search'] = filters['search_text']
            
            # Добавление временных параметров
            if filters['time_range'] != "Все время":
                if filters['time_range'] == "Последний час":
                    start_time = datetime.now() - timedelta(hours=1)
                elif filters['time_range'] == "Последние 24 часа":
                    start_time = datetime.now() - timedelta(days=1)
                elif filters['time_range'] == "Последние 7 дней":
                    start_time = datetime.now() - timedelta(days=7)
                elif filters['time_range'] == "Последние 30 дней":
                    start_time = datetime.now() - timedelta(days=30)
                elif filters['time_range'] == "Произвольный" and filters['start_date']:
                    start_time = datetime.combine(filters['start_date'], datetime.min.time())
                else:
                    start_time = None
                
                if start_time:
                    params['start_time'] = start_time.isoformat()
                
                if filters['end_date']:
                    end_time = datetime.combine(filters['end_date'], datetime.max.time())
                    params['end_time'] = end_time.isoformat()
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/history/queries",
                params=params,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json().get('items', [])
            else:
                st.warning(f"API недоступен (статус: {response.status_code}). Показываем демо-данные.")
                return self._get_demo_history(filters)
                
        except Exception as e:
            st.warning(f"Ошибка соединения с API: {str(e)}. Показываем демо-данные.")
            return self._get_demo_history(filters)
    
    def _get_demo_history(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Создание демо-данных истории для демонстрации"""
        import random
        
        demo_queries = [
            {
                'id': f'demo_{i}',
                'type': random.choice(['search', 'chat', 'upload', 'download', 'analysis']),
                'query_text': f'Демо запрос {i}: поиск информации о {random.choice(["документах", "таблицах", "анализе", "данных"])}',
                'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                'status': random.choice(['success', 'success', 'success', 'error']),  # 75% успешных
                'response_time': round(random.uniform(0.5, 3.0), 2),
                'results_count': random.randint(0, 25),
                'user_id': st.session_state.get('user_info', {}).get('id', 'demo_user'),
                'metadata': {
                    'ip_address': f'192.168.1.{random.randint(1, 254)}',
                    'user_agent': 'Mozilla/5.0 (Demo Browser)',
                    'session_id': f'demo_session_{i}'
                }
            }
            for i in range(1, 21)  # 20 демо записей
        ]
        
        # Фильтрация по типу
        if filters['types']:
            demo_queries = [q for q in demo_queries if q['type'] in filters['types']]
        
        # Фильтрация по статусу
        if filters['status']:
            status_map = {'Успешно': 'success', 'Ошибка': 'error', 'В процессе': 'pending'}
            status_filter = [status_map.get(s, s) for s in filters['status']]
            demo_queries = [q for q in demo_queries if q['status'] in status_filter]
        
        # Фильтрация по тексту
        if filters['search_text']:
            search_text = filters['search_text'].lower()
            demo_queries = [q for q in demo_queries if search_text in q['query_text'].lower()]
        
        # Сортировка
        if filters['sort_by'] == "По дате (новые)":
            demo_queries.sort(key=lambda x: x['timestamp'], reverse=True)
        elif filters['sort_by'] == "По дате (старые)":
            demo_queries.sort(key=lambda x: x['timestamp'])
        elif filters['sort_by'] == "По типу":
            demo_queries.sort(key=lambda x: x['type'])
        elif filters['sort_by'] == "По статусу":
            demo_queries.sort(key=lambda x: x['status'])
        
        return demo_queries
    
    def _render_statistics(self, history_data: List[Dict[str, Any]]):
        """Отображение статистики по истории"""
        st.subheader("📊 Статистика")
        
        if not history_data:
            return
        
        # Подсчет статистики
        total_queries = len(history_data)
        successful_queries = len([q for q in history_data if q.get('status') == 'success'])
        failed_queries = len([q for q in history_data if q.get('status') == 'error'])
        
        # Статистика по типам
        type_stats = {}
        for query in history_data:
            query_type = query.get('type', 'unknown')
            if query_type not in type_stats:
                type_stats[query_type] = 0
            type_stats[query_type] += 1
        
        # Временная статистика
        recent_queries = len([q for q in history_data 
                            if datetime.fromisoformat(q.get('timestamp', '')).replace(tzinfo=None) > 
                            datetime.now() - timedelta(hours=24)])
        
        # Отображение метрик
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Всего запросов",
                value=total_queries,
                delta=f"+{recent_queries} за 24ч"
            )
        
        with col2:
            st.metric(
                label="Успешных",
                value=successful_queries,
                delta=f"{successful_queries/total_queries*100:.1f}%"
            )
        
        with col3:
            st.metric(
                label="Ошибок",
                value=failed_queries,
                delta=f"{failed_queries/total_queries*100:.1f}%"
            )
        
        with col4:
            avg_response_time = sum([q.get('response_time', 0) for q in history_data if q.get('response_time')]) / max(1, total_queries)
            st.metric(
                label="Среднее время ответа",
                value=f"{avg_response_time:.2f}s"
            )
        
        # График по типам
        if type_stats:
            st.write("**Распределение по типам запросов:**")
            type_df = pd.DataFrame([
                {'Тип': self.history_types.get(k, k), 'Количество': v}
                for k, v in type_stats.items()
            ])
            st.bar_chart(type_df.set_index('Тип'))
    
    def _render_history_list(self, history_data: List[Dict[str, Any]], filters: Dict[str, Any]):
        """Отображение списка истории"""
        st.subheader("📋 История запросов")
        
        if not history_data:
            st.info("По выбранным фильтрам ничего не найдено")
            return
        
        # Пагинация
        items_per_page = st.selectbox("Записей на странице", [10, 25, 50, 100], key="history_pagination")
        
        total_pages = (len(history_data) + items_per_page - 1) // items_per_page
        current_page = st.selectbox("Страница", range(1, total_pages + 1), key="history_page")
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_data = history_data[start_idx:end_idx]
        
        # Отображение записей
        for i, query in enumerate(page_data):
            self._render_query_item(query, start_idx + i)
        
        # Навигация по страницам
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.write(f"Страница {current_page} из {total_pages}")
    
    def _render_query_item(self, query: Dict[str, Any], index: int):
        """Отображение отдельного элемента истории"""
        with st.expander(
            f"{self.history_types.get(query.get('type', 'unknown'), '❓')} "
            f"{query.get('query_text', 'Без текста')[:50]}...",
            expanded=False
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Основная информация
                st.write(f"**Запрос:** {query.get('query_text', 'Не указан')}")
                st.write(f"**Тип:** {self.history_types.get(query.get('type', 'unknown'), 'Неизвестно')}")
                st.write(f"**Время:** {query.get('timestamp', 'Не указано')}")
                
                if query.get('response_time'):
                    st.write(f"**Время ответа:** {query.get('response_time'):.2f}с")
                
                # Статус
                status = query.get('status', 'unknown')
                if status == 'success':
                    st.success("✅ Успешно")
                elif status == 'error':
                    st.error(f"❌ Ошибка: {query.get('error_message', 'Неизвестная ошибка')}")
                else:
                    st.warning("⏳ В процессе")
                
                # Результаты (если есть)
                if query.get('results_count'):
                    st.write(f"**Результатов:** {query.get('results_count')}")
                
                # Метаданные
                if query.get('metadata'):
                    with st.expander("📋 Метаданные", expanded=False):
                        st.json(query['metadata'])
            
            with col2:
                # Действия
                if st.button("🔄 Повторить", key=f"repeat_{index}"):
                    self._repeat_query(query)
                
                if st.button("📊 Детали", key=f"details_{index}"):
                    self._show_query_details(query)
                
                if st.button("💾 Экспорт", key=f"export_{index}"):
                    self._export_query(query)
                
                # Удаление (только для своих запросов)
                if query.get('user_id') == st.session_state.get('user_info', {}).get('id'):
                    if st.button("🗑️ Удалить", key=f"delete_{index}"):
                        self._delete_query(query)
    
    def _repeat_query(self, query: Dict[str, Any]):
        """Повторение запроса"""
        query_type = query.get('type')
        query_text = query.get('query_text')
        
        if query_type == 'search':
            st.session_state['search_query'] = query_text
            st.switch_page("🔍 Поиск")
        elif query_type == 'chat':
            st.session_state['chat_message'] = query_text
            st.switch_page("💬 Чат")
        else:
            st.info(f"Повторение запроса типа '{query_type}' не поддерживается")
    
    def _show_query_details(self, query: Dict[str, Any]):
        """Показать детали запроса"""
        st.subheader("📊 Детали запроса")
        
        # Полная информация о запросе
        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = requests.get(
                f"{self.api_base_url}/api/v1/history/queries/{query.get('id')}",
                headers=headers
            )
            
            if response.status_code == 200:
                details = response.json()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Основная информация:**")
                    st.write(f"• ID: {details.get('id')}")
                    st.write(f"• Тип: {details.get('type')}")
                    st.write(f"• Статус: {details.get('status')}")
                    st.write(f"• Время создания: {details.get('timestamp')}")
                    st.write(f"• Время ответа: {details.get('response_time', 'Не указано')}с")
                
                with col2:
                    st.write("**Техническая информация:**")
                    st.write(f"• IP адрес: {details.get('ip_address', 'Не указан')}")
                    st.write(f"• User Agent: {details.get('user_agent', 'Не указан')}")
                    st.write(f"• Сессия: {details.get('session_id', 'Не указана')}")
                
                # Полный текст запроса
                st.write("**Полный текст запроса:**")
                st.text_area("Запрос", value=details.get('query_text', ''), height=100, disabled=True)
                
                # Результаты (если есть)
                if details.get('results'):
                    st.write("**Результаты запроса:**")
                    st.json(details['results'])
                
                # Ошибки (если есть)
                if details.get('error_details'):
                    st.write("**Детали ошибки:**")
                    st.error(details['error_details'])
                
            else:
                st.error(f"Ошибка получения деталей: {response.status_code}")
                
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    def _export_query(self, query: Dict[str, Any]):
        """Экспорт запроса"""
        export_data = {
            'query_id': query.get('id'),
            'type': query.get('type'),
            'query_text': query.get('query_text'),
            'timestamp': query.get('timestamp'),
            'status': query.get('status'),
            'response_time': query.get('response_time'),
            'results_count': query.get('results_count'),
            'metadata': query.get('metadata', {})
        }
        
        # Форматы экспорта
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # JSON
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 JSON",
                data=json_str,
                file_name=f"query_{query.get('id')}.json",
                mime="application/json"
            )
        
        with col2:
            # CSV
            csv_data = pd.DataFrame([export_data])
            csv_str = csv_data.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv_str,
                file_name=f"query_{query.get('id')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # TXT
            txt_content = f"""
Запрос ID: {export_data['query_id']}
Тип: {export_data['type']}
Текст: {export_data['query_text']}
Время: {export_data['timestamp']}
Статус: {export_data['status']}
Время ответа: {export_data['response_time']}с
Количество результатов: {export_data['results_count']}
            """.strip()
            
            st.download_button(
                label="📥 TXT",
                data=txt_content,
                file_name=f"query_{query.get('id')}.txt",
                mime="text/plain"
            )
    
    def _delete_query(self, query: Dict[str, Any]):
        """Удаление запроса из истории"""
        if st.button("🗑️ Подтвердить удаление", key=f"confirm_delete_{query.get('id')}"):
            try:
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                response = requests.delete(
                    f"{self.api_base_url}/api/v1/history/queries/{query.get('id')}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.success("✅ Запрос удален из истории")
                    st.rerun()
                else:
                    st.error(f"Ошибка удаления: {response.status_code}")
                    
            except Exception as e:
                st.error(f"Ошибка: {str(e)}")
    
    def _render_history_actions(self, history_data: List[Dict[str, Any]]):
        """Действия с историей"""
        st.divider()
        st.subheader("🔧 Действия с историей")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Экспорт всей истории", key="export_all_history"):
                self._export_all_history(history_data)
        
        with col2:
            if st.button("🗑️ Очистить историю", key="clear_history"):
                self._clear_history()
        
        with col3:
            if st.button("📈 Анализ трендов", key="analyze_trends"):
                self._analyze_trends(history_data)
        
        with col4:
            if st.button("⚙️ Настройки истории", key="history_settings"):
                self._show_history_settings()
    
    def _export_all_history(self, history_data: List[Dict[str, Any]]):
        """Экспорт всей истории"""
        if not history_data:
            st.warning("История пуста")
            return
        
        # Подготовка данных для экспорта
        export_df = pd.DataFrame(history_data)
        
        # Форматы экспорта
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV
            csv_str = export_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV (вся история)",
                data=csv_str,
                file_name=f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel (требует openpyxl)
            try:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    export_df.to_excel(writer, sheet_name='История запросов', index=False)
                
                st.download_button(
                    label="📥 Excel (вся история)",
                    data=buffer.getvalue(),
                    file_name=f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.warning("📥 Для экспорта в Excel установите openpyxl: `pip install openpyxl`")
                st.download_button(
                    label="📥 Excel (недоступно)",
                    data="",
                    file_name="",
                    disabled=True
                )
        
        with col3:
            # JSON
            json_str = export_df.to_json(orient='records', indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 JSON (вся история)",
                data=json_str,
                file_name=f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    def _clear_history(self):
        """Очистка истории"""
        if st.button("🗑️ Подтвердить очистку всей истории", key="confirm_clear_all"):
            try:
                headers = {}
                if self.access_token:
                    headers["Authorization"] = f"Bearer {self.access_token}"
                
                response = requests.delete(
                    f"{self.api_base_url}/api/v1/history/queries/clear",
                    headers=headers
                )
                
                if response.status_code == 200:
                    st.success("✅ Вся история очищена")
                    st.rerun()
                else:
                    st.error(f"Ошибка очистки: {response.status_code}")
                    
            except Exception as e:
                st.error(f"Ошибка: {str(e)}")
    
    def _analyze_trends(self, history_data: List[Dict[str, Any]]):
        """Анализ трендов в истории"""
        st.subheader("📈 Анализ трендов")
        
        if not history_data:
            st.warning("Недостаточно данных для анализа")
            return
        
        # Анализ по времени
        df = pd.DataFrame(history_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Активность по часам
            hourly_activity = df.groupby('hour').size()
            st.write("**Активность по часам:**")
            st.bar_chart(hourly_activity)
        
        with col2:
            # Активность по дням недели
            daily_activity = df.groupby('day_of_week').size()
            st.write("**Активность по дням недели:**")
            st.bar_chart(daily_activity)
        
        # Тренд по времени
        st.write("**Тренд активности по времени:**")
        df['date'] = df['timestamp'].dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')
        st.line_chart(daily_counts.set_index('date'))
    
    def _show_history_settings(self):
        """Настройки истории"""
        st.subheader("⚙️ Настройки истории")
        
        st.info("Настройки истории запросов будут доступны в следующем обновлении")
        
        # Заглушки для будущих настроек
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("Сохранять историю поиска", value=True, disabled=True)
            st.checkbox("Сохранять историю чата", value=True, disabled=True)
            st.checkbox("Сохранять историю загрузок", value=True, disabled=True)
        
        with col2:
            retention_days = st.selectbox(
                "Хранить историю (дней)",
                [7, 30, 90, 365, -1],
                index=1,
                disabled=True
            )
            
            if retention_days == -1:
                st.caption("Бессрочно")
            else:
                st.caption(f"{retention_days} дней")
    
    def _render_quick_access(self, history_data: List[Dict[str, Any]]):
        """Быстрый доступ к частым запросам"""
        st.subheader("⚡ Быстрый доступ")
        
        if not history_data:
            return
        
        # Анализ частых запросов
        query_counts = {}
        successful_queries = [q for q in history_data if q.get('status') == 'success']
        
        for query in successful_queries:
            query_text = query.get('query_text', '')
            if query_text:
                # Нормализуем запрос (убираем лишние пробелы, приводим к нижнему регистру)
                normalized = ' '.join(query_text.lower().split())
                if len(normalized) > 10:  # Игнорируем слишком короткие запросы
                    query_counts[normalized] = query_counts.get(normalized, 0) + 1
        
        # Сортируем по частоте
        frequent_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if frequent_queries:
            st.write("**Часто используемые запросы:**")
            
            for i, (query, count) in enumerate(frequent_queries):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"{i+1}. {query}")
                
                with col2:
                    st.write(f"({count} раз)")
                
                with col3:
                    if st.button("🔄 Повторить", key=f"quick_repeat_{i}"):
                        self._repeat_quick_query(query)
        
        # Быстрые действия
        st.write("**Быстрые действия:**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Последний поиск", key="quick_last_search"):
                self._repeat_last_query('search')
        
        with col2:
            if st.button("💬 Последний чат", key="quick_last_chat"):
                self._repeat_last_query('chat')
        
        with col3:
            if st.button("📊 Анализ активности", key="quick_activity_analysis"):
                self._show_activity_analysis(history_data)
        
        with col4:
            if st.button("📈 Тренды запросов", key="quick_query_trends"):
                self._show_query_trends(history_data)
    
    def _repeat_quick_query(self, query_text: str):
        """Повторение быстрого запроса"""
        # Определяем тип запроса по содержимому
        if any(word in query_text.lower() for word in ['найди', 'поиск', 'искать', 'найти']):
            st.session_state['search_query'] = query_text
            st.switch_page("🔍 Поиск")
        else:
            st.session_state['chat_message'] = query_text
            st.switch_page("💬 Чат")
    
    def _repeat_last_query(self, query_type: str):
        """Повторение последнего запроса определенного типа"""
        if not hasattr(st.session_state, 'query_history') or not st.session_state.query_history:
            st.warning("История запросов пуста")
            return
        
        # Ищем последний запрос нужного типа
        last_query = None
        for query in reversed(st.session_state.query_history):
            if query.get('type') == query_type:
                last_query = query
                break
        
        if last_query:
            query_text = last_query.get('query_text', '')
            if query_type == 'search':
                st.session_state['search_query'] = query_text
                st.switch_page("🔍 Поиск")
            elif query_type == 'chat':
                st.session_state['chat_message'] = query_text
                st.switch_page("💬 Чат")
        else:
            st.warning(f"Не найдено запросов типа '{query_type}'")
    
    def _show_activity_analysis(self, history_data: List[Dict[str, Any]]):
        """Анализ активности пользователя"""
        st.subheader("📊 Анализ активности")
        
        if not history_data:
            st.warning("Недостаточно данных для анализа")
            return
        
        # Анализ по времени
        df = pd.DataFrame(history_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['date'] = df['timestamp'].dt.date
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Активность по часам
            hourly_activity = df.groupby('hour').size()
            st.write("**Активность по часам:**")
            st.bar_chart(hourly_activity)
        
        with col2:
            # Активность по дням недели
            daily_activity = df.groupby('day_of_week').size()
            st.write("**Активность по дням недели:**")
            st.bar_chart(daily_activity)
        
        # Статистика по типам запросов
        st.write("**Статистика по типам запросов:**")
        type_stats = df['type'].value_counts()
        st.bar_chart(type_stats)
        
        # Успешность запросов
        success_rate = len(df[df['status'] == 'success']) / len(df) * 100
        st.metric("Успешность запросов", f"{success_rate:.1f}%")
        
        # Среднее время ответа
        avg_response_time = df['response_time'].mean()
        st.metric("Среднее время ответа", f"{avg_response_time:.2f}с")
    
    def _show_query_trends(self, history_data: List[Dict[str, Any]]):
        """Анализ трендов запросов"""
        st.subheader("📈 Тренды запросов")
        
        if not history_data:
            st.warning("Недостаточно данных для анализа трендов")
            return
        
        df = pd.DataFrame(history_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        # Тренд по дням
        daily_counts = df.groupby('date').size().reset_index(name='count')
        st.write("**Количество запросов по дням:**")
        st.line_chart(daily_counts.set_index('date'))
        
        # Тренд по типам запросов
        st.write("**Тренд по типам запросов:**")
        type_trends = df.groupby(['date', 'type']).size().unstack(fill_value=0)
        st.line_chart(type_trends)
        
        # Анализ популярных слов
        all_queries = ' '.join(df['query_text'].fillna('').astype(str))
        words = all_queries.lower().split()
        
        # Убираем стоп-слова
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'о', 'у', 'за', 'под', 'над', 'при', 'через', 'между', 'без', 'про', 'что', 'как', 'где', 'когда', 'почему', 'какой', 'какая', 'какое', 'какие'}
        words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        if words:
            from collections import Counter
            word_counts = Counter(words)
            top_words = word_counts.most_common(10)
            
            st.write("**Популярные слова в запросах:**")
            for word, count in top_words:
                st.write(f"• {word}: {count}")
