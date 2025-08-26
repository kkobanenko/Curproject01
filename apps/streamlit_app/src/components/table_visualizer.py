"""
Компонент для визуализации таблиц
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, Any, List, Optional
import json
from io import BytesIO


class TableVisualizer:
    """Компонент для визуализации табличных данных"""
    
    def __init__(self):
        self.chart_types = {
            'line': self._create_line_chart,
            'bar': self._create_bar_chart,
            'scatter': self._create_scatter_chart,
            'pie': self._create_pie_chart,
            'histogram': self._create_histogram,
            'box': self._create_box_plot,
            'heatmap': self._create_heatmap,
            '3d_scatter': self._create_3d_scatter,
            'area': self._create_area_chart,
            'violin': self._create_violin_plot
        }
    
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
            list(self.chart_types.keys()),
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
        
        elif chart_type == 'pie':
            value_column = st.selectbox("Столбец значений", numeric_columns if numeric_columns else df.columns.tolist())
            label_column = st.selectbox("Столбец меток", categorical_columns if categorical_columns else df.columns.tolist())
        
        elif chart_type == 'histogram':
            column = st.selectbox("Столбец для гистограммы", numeric_columns if numeric_columns else df.columns.tolist())
        
        elif chart_type == 'box':
            column = st.selectbox("Столбец для box plot", numeric_columns if numeric_columns else df.columns.tolist())
        
        elif chart_type == 'heatmap':
            st.info("Для тепловой карты будут использованы все числовые столбцы")
        
        elif chart_type == '3d_scatter':
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("Ось X", numeric_columns if numeric_columns else df.columns.tolist())
            with col2:
                y_axis = st.selectbox("Ось Y", numeric_columns if numeric_columns else df.columns.tolist())
            with col3:
                z_axis = st.selectbox("Ось Z", numeric_columns if numeric_columns else df.columns.tolist())
        
        # Создание графика
        if chart_type in self.chart_types:
            try:
                if chart_type in ['line', 'bar', 'scatter', 'area'] and y_axis:
                    fig = self.chart_types[chart_type](df, x_axis, y_axis, table_info)
                elif chart_type == 'pie':
                    fig = self.chart_types[chart_type](df, label_column, value_column, table_info)
                elif chart_type in ['histogram', 'box']:
                    fig = self.chart_types[chart_type](df, column, table_info)
                elif chart_type == 'heatmap':
                    fig = self.chart_types[chart_type](df, table_info)
                elif chart_type == '3d_scatter':
                    fig = self.chart_types[chart_type](df, x_axis, y_axis, z_axis, table_info)
                else:
                    st.warning("Выберите подходящие столбцы для визуализации")
                    return
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Настройки графика
                    self._render_chart_settings(fig)
                    
            except Exception as e:
                st.error(f"Ошибка создания графика: {str(e)}")
    
    def _create_line_chart(self, df: pd.DataFrame, x_col: str, y_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание линейного графика"""
        fig = px.line(df, x=x_col, y=y_col, title=f"Линейный график: {y_col} по {x_col}")
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            hovermode='x unified'
        )
        return fig
    
    def _create_bar_chart(self, df: pd.DataFrame, x_col: str, y_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание столбчатого графика"""
        fig = px.bar(df, x=x_col, y=y_col, title=f"Столбчатый график: {y_col} по {x_col}")
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        return fig
    
    def _create_scatter_chart(self, df: pd.DataFrame, x_col: str, y_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание точечного графика"""
        fig = px.scatter(df, x=x_col, y=y_col, title=f"Точечный график: {y_col} vs {x_col}")
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        return fig
    
    def _create_pie_chart(self, df: pd.DataFrame, label_col: str, value_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание круговой диаграммы"""
        fig = px.pie(df, names=label_col, values=value_col, title=f"Круговая диаграмма: {value_col}")
        return fig
    
    def _create_histogram(self, df: pd.DataFrame, column: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание гистограммы"""
        fig = px.histogram(df, x=column, title=f"Гистограмма: {column}")
        fig.update_layout(
            xaxis_title=column,
            yaxis_title="Частота"
        )
        return fig
    
    def _create_box_plot(self, df: pd.DataFrame, column: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание box plot"""
        fig = px.box(df, y=column, title=f"Box Plot: {column}")
        fig.update_layout(
            yaxis_title=column
        )
        return fig
    
    def _create_heatmap(self, df: pd.DataFrame, table_info: Dict[str, Any]) -> go.Figure:
        """Создание тепловой карты корреляций"""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            st.error("Нет числовых столбцов для тепловой карты")
            return None
        
        corr_matrix = numeric_df.corr()
        fig = px.imshow(
            corr_matrix,
            title="Тепловая карта корреляций",
            color_continuous_scale='RdBu',
            aspect='auto'
        )
        fig.update_layout(
            xaxis_title="Столбцы",
            yaxis_title="Столбцы"
        )
        return fig
    
    def _create_3d_scatter(self, df: pd.DataFrame, x_col: str, y_col: str, z_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание 3D точечного графика"""
        fig = px.scatter_3d(
            df, 
            x=x_col, 
            y=y_col, 
            z=z_col, 
            title=f"3D график: {x_col} vs {y_col} vs {z_col}"
        )
        return fig
    
    def _create_area_chart(self, df: pd.DataFrame, x_col: str, y_col: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание площадного графика"""
        fig = px.area(df, x=x_col, y=y_col, title=f"Площадной график: {y_col} по {x_col}")
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col
        )
        return fig
    
    def _create_violin_plot(self, df: pd.DataFrame, column: str, table_info: Dict[str, Any]) -> go.Figure:
        """Создание violin plot"""
        fig = px.violin(df, y=column, title=f"Violin Plot: {column}")
        fig.update_layout(
            yaxis_title=column
        )
        return fig
    
    def _render_chart_settings(self, fig: go.Figure):
        """Настройки графика"""
        with st.expander("⚙️ Настройки графика", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Размер графика
                height = st.slider("Высота", 400, 800, 500, 50)
                fig.update_layout(height=height)
                
                # Цветовая схема
                color_schemes = ['plotly', 'plotly_dark', 'plotly_white', 'ggplot2', 'seaborn']
                color_scheme = st.selectbox("Цветовая схема", color_schemes)
                fig.update_layout(template=color_scheme)
            
            with col2:
                # Показ легенды
                show_legend = st.checkbox("Показать легенду", value=True)
                fig.update_layout(showlegend=show_legend)
                
                # Анимация
                enable_animation = st.checkbox("Включить анимацию", value=False)
                if enable_animation:
                    fig.update_layout(
                        updatemenus=[{
                            'buttons': [
                                {'label': 'Play', 'method': 'animate', 'args': [None]}
                            ],
                            'direction': 'left',
                            'pad': {'r': 10, 't': 87},
                            'showactive': False,
                            'type': 'buttons',
                            'x': 0.1,
                            'xanchor': 'right',
                            'y': 0,
                            'yanchor': 'top'
                        }]
                    )
    
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
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=numeric_df.columns.tolist()
                )
                
                for i, col in enumerate(numeric_df.columns):
                    row = (i // 2) + 1
                    col_idx = (i % 2) + 1
                    
                    fig.add_trace(
                        go.Histogram(x=numeric_df[col], name=col),
                        row=row, col=col_idx
                    )
                
                fig.update_layout(height=600, title_text="Распределения числовых столбцов")
                st.plotly_chart(fig, use_container_width=True)
        
        if not categorical_df.empty:
            # Статистика категориальных столбцов
            st.write("**Категориальные столбцы:**")
            for col in categorical_df.columns:
                value_counts = categorical_df[col].value_counts()
                if len(value_counts) <= 10:  # Показываем только если не слишком много уникальных значений
                    fig = px.pie(
                        values=value_counts.values,
                        names=value_counts.index,
                        title=f"Распределение: {col}"
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
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
                fig = px.scatter(df, x=col_x, y=col_y, title=f"{col_x} vs {col_y}")
                st.plotly_chart(fig, use_container_width=True)
                
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
            # Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            st.download_button(
                label="📥 Скачать Excel",
                data=buffer.getvalue(),
                file_name=f"{table_info.get('title', 'table')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
