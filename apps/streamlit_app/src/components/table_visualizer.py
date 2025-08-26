"""
Компонент для визуализации таблиц
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json
from io import BytesIO


class TableVisualizer:
    """Компонент для визуализации табличных данных"""
    
    def __init__(self):
        self.chart_types = ['line', 'bar', 'scatter', 'pie', 'histogram', 'box', 'heatmap', 'area']
    
    def render(self, table_data: Dict[str, Any], table_info: Dict[str, Any]):
        """Основной метод рендеринга визуализации таблицы"""
        st.header(f"📊 Визуализация таблицы: {table_info.get('title', 'Без названия')}")
        
        # Информация о таблице
        self._render_table_info(table_info)
        
        # Преобразование данных в DataFrame
        df = self._prepare_dataframe(table_data)
        
        if df is None or df.empty:
            st.error("Не удалось загрузить данные таблицы")
            return
        
        # Основная визуализация
        self._render_main_visualization(df, table_info)
        
        # Дополнительные графики
        self._render_additional_charts(df, table_info)
        
        # Статистика и анализ
        self._render_statistics(df, table_info)
        
        # Экспорт данных
        self._render_export_options(df, table_info)
    
    def _render_table_info(self, table_info: Dict[str, Any]):
        """Отображение информации о таблице"""
        with st.expander("📋 Информация о таблице", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Основные параметры:**")
                st.write(f"• Размер: {table_info.get('rows', 0)} × {table_info.get('columns', 0)}")
                st.write(f"• Тип: {table_info.get('type', 'Неизвестно')}")
                st.write(f"• Источник: {table_info.get('source', 'Неизвестно')}")
            
            with col2:
                st.write("**Качество данных:**")
                st.write(f"• Заполненность: {table_info.get('completeness', 'Неизвестно')}")
                st.write(f"• Уникальность: {table_info.get('uniqueness', 'Неизвестно')}")
                st.write(f"• Консистентность: {table_info.get('consistency', 'Неизвестно')}")
    
    def _prepare_dataframe(self, table_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Подготовка DataFrame из данных таблицы"""
        try:
            if isinstance(table_data, list):
                return pd.DataFrame(table_data)
            elif isinstance(table_data, dict) and 'data' in table_data:
                return pd.DataFrame(table_data['data'])
            elif isinstance(table_data, dict) and 'rows' in table_data:
                return pd.DataFrame(table_data['rows'])
            else:
                st.error("Неподдерживаемый формат данных таблицы")
                return None
        except Exception as e:
            st.error(f"Ошибка создания DataFrame: {str(e)}")
            return None
    
    def _render_main_visualization(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Основная визуализация таблицы"""
        st.subheader("📈 Основная визуализация")
        
        # Выбор типа графика
        chart_type = st.selectbox(
            "Выберите тип графика",
            self.chart_types,
            key=f"main_chart_{table_info.get('id', 'default')}"
        )
        
        # Выбор осей
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
        
        if chart_type in ['line', 'bar', 'scatter', 'area']:
            col1, col2 = st.columns(2)
            
            with col1:
                x_axis = st.selectbox("Ось X", df.columns.tolist(), key=f"x_axis_{chart_type}")
            
            with col2:
                if numeric_columns:
                    y_axis = st.selectbox("Ось Y", numeric_columns, key=f"y_axis_{chart_type}")
                else:
                    y_axis = None
                    st.warning("Нет числовых столбцов для оси Y")
            
            if y_axis:
                self._create_simple_chart(df, x_axis, y_axis, chart_type)
        
        elif chart_type == 'pie':
            if numeric_columns and categorical_columns:
                value_column = st.selectbox("Столбец значений", numeric_columns)
                label_column = st.selectbox("Столбец меток", categorical_columns)
                self._create_pie_chart(df, label_column, value_column)
        
        elif chart_type == 'histogram':
            if numeric_columns:
                column = st.selectbox("Столбец для гистограммы", numeric_columns)
                self._create_histogram(df, column)
        
        elif chart_type == 'box':
            if numeric_columns:
                column = st.selectbox("Столбец для box plot", numeric_columns)
                self._create_box_plot(df, column)
        
        elif chart_type == 'heatmap':
            if len(numeric_columns) > 1:
                self._create_heatmap(df)
            else:
                st.warning("Для тепловой карты нужно минимум 2 числовых столбца")
    
    def _create_simple_chart(self, df: pd.DataFrame, x_col: str, y_col: str, chart_type: str):
        """Создание простых графиков с помощью Streamlit"""
        chart_data = pd.DataFrame({
            'x': df[x_col],
            'y': df[y_col]
        })
        
        if chart_type == 'line':
            st.line_chart(chart_data.set_index('x'))
        elif chart_type == 'bar':
            st.bar_chart(chart_data.set_index('x'))
        elif chart_type == 'scatter':
            st.scatter_chart(chart_data, x='x', y='y')
        elif chart_type == 'area':
            st.area_chart(chart_data.set_index('x'))
    
    def _create_pie_chart(self, df: pd.DataFrame, label_col: str, value_col: str):
        """Создание круговой диаграммы"""
        # Группируем данные
        grouped_data = df.groupby(label_col)[value_col].sum().reset_index()
        
        # Показываем данные в таблице
        st.write("**Данные для круговой диаграммы:**")
        st.dataframe(grouped_data)
        
        # Простая визуализация
        st.write("**Распределение по категориям:**")
        for _, row in grouped_data.iterrows():
            percentage = (row[value_col] / grouped_data[value_col].sum()) * 100
            st.write(f"• {row[label_col]}: {row[value_col]} ({percentage:.1f}%)")
    
    def _create_histogram(self, df: pd.DataFrame, column: str):
        """Создание гистограммы"""
        # Показываем данные
        st.write(f"**Гистограмма для столбца: {column}**")
        
        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Минимум", f"{df[column].min():.2f}")
        with col2:
            st.metric("Среднее", f"{df[column].mean():.2f}")
        with col3:
            st.metric("Максимум", f"{df[column].max():.2f}")
        
        # Простая гистограмма
        st.bar_chart(df[column].value_counts().sort_index())
    
    def _create_box_plot(self, df: pd.DataFrame, column: str):
        """Создание box plot"""
        st.write(f"**Box Plot для столбца: {column}**")
        
        # Статистика
        stats = df[column].describe()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Q1", f"{stats['25%']:.2f}")
        with col2:
            st.metric("Медиана", f"{stats['50%']:.2f}")
        with col3:
            st.metric("Q3", f"{stats['75%']:.2f}")
        with col4:
            st.metric("IQR", f"{stats['75%'] - stats['25%']:.2f}")
        
        # Показываем выбросы
        Q1 = stats['25%']
        Q3 = stats['75%']
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
        if not outliers.empty:
            st.write(f"**Выбросы ({len(outliers)}):**")
            st.dataframe(outliers)
    
    def _create_heatmap(self, df: pd.DataFrame):
        """Создание тепловой карты корреляций"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            st.error("Нет числовых столбцов для тепловой карты")
            return
        
        # Корреляционная матрица
        corr_matrix = numeric_df.corr()
        
        st.write("**Корреляционная матрица:**")
        st.dataframe(corr_matrix)
        
        # Интерпретация
        st.write("**Интерпретация корреляций:**")
        for i, col1 in enumerate(corr_matrix.columns):
            for j, col2 in enumerate(corr_matrix.columns):
                if i < j:  # Показываем только верхний треугольник
                    corr_value = corr_matrix.loc[col1, col2]
                    if abs(corr_value) > 0.7:
                        strength = "сильная"
                    elif abs(corr_value) > 0.3:
                        strength = "умеренная"
                    else:
                        strength = "слабая"
                    
                    if corr_value > 0:
                        direction = "положительная"
                    else:
                        direction = "отрицательная"
                    
                    st.write(f"• {col1} ↔ {col2}: {corr_value:.3f} ({strength} {direction} корреляция)")
    
    def _render_additional_charts(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Дополнительные графики"""
        st.subheader("📊 Дополнительные графики")
        
        # Автоматический анализ данных
        if st.checkbox("Показать автоматический анализ данных", value=False):
            self._render_auto_analysis(df, table_info)
        
        # Сравнение столбцов
        if st.checkbox("Сравнение столбцов", value=False):
            self._render_column_comparison(df, table_info)
    
    def _render_auto_analysis(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Автоматический анализ данных"""
        st.subheader("🤖 Автоматический анализ")
        
        numeric_df = df.select_dtypes(include=[np.number])
        categorical_df = df.select_dtypes(include=['object'])
        
        if not numeric_df.empty:
            # Статистика числовых столбцов
            st.write("**Числовые столбцы:**")
            st.dataframe(numeric_df.describe())
            
            # Распределения
            if len(numeric_df.columns) <= 4:
                st.write("**Распределения числовых столбцов:**")
                for col in numeric_df.columns:
                    st.write(f"**{col}:**")
                    st.bar_chart(numeric_df[col].value_counts().sort_index())
        
        if not categorical_df.empty:
            # Статистика категориальных столбцов
            st.write("**Категориальные столбцы:**")
            for col in categorical_df.columns:
                value_counts = categorical_df[col].value_counts()
                if len(value_counts) <= 10:  # Показываем только если не слишком много уникальных значений
                    st.write(f"**Распределение: {col}**")
                    st.bar_chart(value_counts)
    
    def _render_column_comparison(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Сравнение столбцов"""
        st.subheader("🔍 Сравнение столбцов")
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_columns) >= 2:
            col1, col2 = st.columns(2)
            
            with col1:
                col_x = st.selectbox("Столбец X", numeric_columns, key="comp_x")
            
            with col2:
                col_y = st.selectbox("Столбец Y", numeric_columns, key="comp_y")
            
            if col_x != col_y:
                # Scatter plot
                chart_data = pd.DataFrame({
                    'x': df[col_x],
                    'y': df[col_y]
                })
                st.scatter_chart(chart_data, x='x', y='y')
                
                # Корреляция
                correlation = df[col_x].corr(df[col_y])
                st.metric("Корреляция", f"{correlation:.3f}")
    
    def _render_statistics(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Статистика и анализ"""
        st.subheader("📈 Статистика и анализ")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Основная статистика
            st.write("**Основная статистика:**")
            st.dataframe(df.describe())
        
        with col2:
            # Информация о данных
            st.write("**Информация о данных:**")
            
            buffer = BytesIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue().decode()
            
            st.text_area("Информация", value=info_str, height=200, disabled=True)
            
            # Проверка на пропущенные значения
            missing_data = df.isnull().sum()
            if missing_data.sum() > 0:
                st.write("**Пропущенные значения:**")
                st.dataframe(missing_data[missing_data > 0])
            else:
                st.success("✅ Пропущенных значений нет")
    
    def _render_export_options(self, df: pd.DataFrame, table_info: Dict[str, Any]):
        """Опции экспорта данных"""
        st.subheader("💾 Экспорт данных")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Скачать CSV",
                data=csv,
                file_name=f"{table_info.get('title', 'table')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel (требует openpyxl)
            try:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Sheet1', index=False)
                
                st.download_button(
                    label="📥 Скачать Excel",
                    data=buffer.getvalue(),
                    file_name=f"{table_info.get('title', 'table')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.warning("📥 Для экспорта в Excel установите openpyxl: `pip install openpyxl`")
                st.download_button(
                    label="📥 Скачать Excel (недоступно)",
                    data="",
                    file_name="",
                    disabled=True
                )
        
        with col3:
            # JSON
            json_str = df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Скачать JSON",
                data=json_str,
                file_name=f"{table_info.get('title', 'table')}.json",
                mime="application/json"
            )
