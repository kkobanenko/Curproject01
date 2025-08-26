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
            'analysis': '📊 Анализ'
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
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get('items', [])
            else:
                st.error(f"Ошибка получения истории: {response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"Ошибка соединения: {str(e)}")
            return None
    
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
            # Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name='История запросов', index=False)
            
            st.download_button(
                label="📥 Excel (вся история)",
                data=buffer.getvalue(),
                file_name=f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
