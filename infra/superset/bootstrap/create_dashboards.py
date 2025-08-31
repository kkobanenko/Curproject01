"""
Скрипт создания дашбордов для RAG платформы
"""
import os
import sys
import json
import logging
from datetime import datetime

# Добавляем путь к Superset
sys.path.append('/app')

from superset import db
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.models.datasource import Datasource
from superset.connectors.sqla.models import SqlaTable
from superset.utils.core import get_example_default_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_quality_dashboard():
    """Создание дашборда качества RAG"""
    try:
        # Получаем источник данных
        datasource = db.session.query(SqlaTable).filter_by(
            table_name='search_quality_metrics'
        ).first()
        
        if not datasource:
            logger.error("Search quality metrics datasource not found")
            return None
        
        # Создаем чарты
        charts = []
        
        # 1. Средние метрики качества по времени
        avg_quality_chart = Slice(
            slice_name="Средние метрики качества по времени",
            datasource_type='table',
            datasource_id=datasource.id,
            viz_type='line',
            params=json.dumps({
                "metrics": [
                    {"expressionType": "SIMPLE", "column": {"column_name": "relevance_score", "type": "FLOAT"}, "label": "Релевантность", "optionName": "metric_1"},
                    {"expressionType": "SIMPLE", "column": {"column_name": "precision_score", "type": "FLOAT"}, "label": "Точность", "optionName": "metric_2"},
                    {"expressionType": "SIMPLE", "column": {"column_name": "recall_score", "type": "FLOAT"}, "label": "Полнота", "optionName": "metric_3"},
                    {"expressionType": "SIMPLE", "column": {"column_name": "f1_score", "type": "FLOAT"}, "label": "F1-мера", "optionName": "metric_4"}
                ],
                "groupby": ["timestamp"],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Тренды качества поиска по времени"
        )
        db.session.add(avg_quality_chart)
        charts.append(avg_quality_chart)
        
        # 2. Распределение качества ответов
        quality_distribution_chart = Slice(
            slice_name="Распределение качества ответов",
            datasource_type='table',
            datasource_id=datasource.id,
            viz_type='histogram',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "response_quality", "type": "FLOAT"}, "label": "Качество ответов", "optionName": "metric_1"}],
                "adhoc_filters": [],
                "row_limit": 1000,
                "bins": 20
            }),
            description="Гистограмма распределения качества ответов"
        )
        db.session.add(quality_distribution_chart)
        charts.append(quality_distribution_chart)
        
        # 3. Качество по тенантам
        tenant_quality_chart = Slice(
            slice_name="Качество поиска по тенантам",
            datasource_type='table',
            datasource_id=datasource.id,
            viz_type='bar',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "f1_score", "type": "FLOAT"}, "label": "F1-мера", "optionName": "metric_1"}],
                "groupby": ["tenant_id"],
                "adhoc_filters": [],
                "row_limit": 100
            }),
            description="Сравнение качества поиска между тенантами"
        )
        db.session.add(tenant_quality_chart)
        charts.append(tenant_quality_chart)
        
        # 4. Корреляция метрик качества
        quality_correlation_chart = Slice(
            slice_name="Корреляция метрик качества",
            datasource_type='table',
            datasource_id=datasource.id,
            viz_type='heatmap',
            params=json.dumps({
                "all_columns_x": "relevance_score",
                "all_columns_y": "precision_score",
                "metric": {"expressionType": "SIMPLE", "column": {"column_name": "f1_score", "type": "FLOAT"}, "label": "F1-мера", "optionName": "metric_1"},
                "adhoc_filters": [],
                "row_limit": 1000
            }),
            description="Корреляция между различными метриками качества"
        )
        db.session.add(quality_correlation_chart)
        charts.append(quality_correlation_chart)
        
        db.session.commit()
        
        # Создаем дашборд
        dashboard = Dashboard(
            dashboard_title="Качество RAG системы",
            slug="rag-quality-dashboard",
            position_json=json.dumps({
                "DASHBOARD_VERSION_KEY": "v2",
                "DASHBOARD_ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
                "GRID_ID": {
                    "id": "GRID_ID",
                    "type": "GRID",
                    "children": [
                        {"id": "CHART-1", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-2", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-3", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-4", "type": "CHART", "meta": {"width": 6, "height": 4}}
                    ]
                }
            }),
            css="",
            json_metadata=json.dumps({
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "color_scheme": None,
                "label_colors": {}
            }),
            slices=[chart.id for chart in charts],
            published=True
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        logger.info("Quality dashboard created successfully")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error creating quality dashboard: {e}")
        db.session.rollback()
        return None


def create_performance_dashboard():
    """Создание дашборда производительности"""
    try:
        # Получаем источники данных
        system_metrics_ds = db.session.query(SqlaTable).filter_by(
            table_name='system_metrics'
        ).first()
        
        resource_usage_ds = db.session.query(SqlaTable).filter_by(
            table_name='resource_usage_metrics'
        ).first()
        
        api_metrics_ds = db.session.query(SqlaTable).filter_by(
            table_name='api_metrics'
        ).first()
        
        if not all([system_metrics_ds, resource_usage_ds, api_metrics_ds]):
            logger.error("Required datasources not found for performance dashboard")
            return None
        
        charts = []
        
        # 1. Использование CPU по сервисам
        cpu_usage_chart = Slice(
            slice_name="Использование CPU по сервисам",
            datasource_type='table',
            datasource_id=resource_usage_ds.id,
            viz_type='line',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "cpu_usage_percent", "type": "FLOAT"}, "label": "CPU %", "optionName": "metric_1"}],
                "groupby": ["service"],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Использование CPU по сервисам во времени"
        )
        db.session.add(cpu_usage_chart)
        charts.append(cpu_usage_chart)
        
        # 2. Использование памяти
        memory_usage_chart = Slice(
            slice_name="Использование памяти",
            datasource_type='table',
            datasource_id=resource_usage_ds.id,
            viz_type='area',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "memory_usage_mb", "type": "INTEGER"}, "label": "Память (MB)", "optionName": "metric_1"}],
                "groupby": ["service"],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Использование памяти по сервисам"
        )
        db.session.add(memory_usage_chart)
        charts.append(memory_usage_chart)
        
        # 3. Время ответа API
        api_response_time_chart = Slice(
            slice_name="Время ответа API",
            datasource_type='table',
            datasource_id=api_metrics_ds.id,
            viz_type='line',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "response_time_ms", "type": "INTEGER"}, "label": "Время ответа (мс)", "optionName": "metric_1"}],
                "groupby": ["endpoint"],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Время ответа API эндпоинтов"
        )
        db.session.add(api_response_time_chart)
        charts.append(api_response_time_chart)
        
        # 4. Активные соединения
        connections_chart = Slice(
            slice_name="Активные соединения",
            datasource_type='table',
            datasource_id=resource_usage_ds.id,
            viz_type='bar',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "active_connections", "type": "INTEGER"}, "label": "Соединения", "optionName": "metric_1"}],
                "groupby": ["service"],
                "adhoc_filters": [],
                "row_limit": 100
            }),
            description="Количество активных соединений по сервисам"
        )
        db.session.add(connections_chart)
        charts.append(connections_chart)
        
        # 5. Коды ответов API
        status_codes_chart = Slice(
            slice_name="Коды ответов API",
            datasource_type='table',
            datasource_id=api_metrics_ds.id,
            viz_type='pie',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "status_code", "type": "INTEGER"}, "label": "Количество", "optionName": "metric_1"}],
                "groupby": ["status_code"],
                "adhoc_filters": [],
                "row_limit": 100
            }),
            description="Распределение HTTP кодов ответов"
        )
        db.session.add(status_codes_chart)
        charts.append(status_codes_chart)
        
        db.session.commit()
        
        # Создаем дашборд
        dashboard = Dashboard(
            dashboard_title="Производительность системы",
            slug="rag-performance-dashboard",
            position_json=json.dumps({
                "DASHBOARD_VERSION_KEY": "v2",
                "DASHBOARD_ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
                "GRID_ID": {
                    "id": "GRID_ID",
                    "type": "GRID",
                    "children": [
                        {"id": "CHART-1", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-2", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-3", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-4", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-5", "type": "CHART", "meta": {"width": 12, "height": 4}}
                    ]
                }
            }),
            css="",
            json_metadata=json.dumps({
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "color_scheme": None,
                "label_colors": {}
            }),
            slices=[chart.id for chart in charts],
            published=True
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        logger.info("Performance dashboard created successfully")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error creating performance dashboard: {e}")
        db.session.rollback()
        return None


def create_usage_dashboard():
    """Создание дашборда использования"""
    try:
        # Получаем источники данных
        search_metrics_ds = db.session.query(SqlaTable).filter_by(
            table_name='search_metrics'
        ).first()
        
        chat_metrics_ds = db.session.query(SqlaTable).filter_by(
            table_name='chat_metrics'
        ).first()
        
        if not all([search_metrics_ds, chat_metrics_ds]):
            logger.error("Required datasources not found for usage dashboard")
            return None
        
        charts = []
        
        # 1. Количество поисковых запросов по времени
        search_volume_chart = Slice(
            slice_name="Объем поисковых запросов",
            datasource_type='table',
            datasource_id=search_metrics_ds.id,
            viz_type='line',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "query_text", "type": "TEXT"}, "label": "Запросы", "optionName": "metric_1", "aggregate": "COUNT"}],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Количество поисковых запросов по времени"
        )
        db.session.add(search_volume_chart)
        charts.append(search_volume_chart)
        
        # 2. Популярные запросы
        popular_queries_chart = Slice(
            slice_name="Популярные поисковые запросы",
            datasource_type='table',
            datasource_id=search_metrics_ds.id,
            viz_type='table',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "query_text", "type": "TEXT"}, "label": "Количество", "optionName": "metric_1", "aggregate": "COUNT"}],
                "groupby": ["query_text"],
                "adhoc_filters": [],
                "row_limit": 20,
                "order_desc": True
            }),
            description="Топ-20 самых популярных поисковых запросов"
        )
        db.session.add(popular_queries_chart)
        charts.append(popular_queries_chart)
        
        # 3. Активность по тенантам
        tenant_activity_chart = Slice(
            slice_name="Активность по тенантам",
            datasource_type='table',
            datasource_id=search_metrics_ds.id,
            viz_type='bar',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "query_text", "type": "TEXT"}, "label": "Запросы", "optionName": "metric_1", "aggregate": "COUNT"}],
                "groupby": ["tenant_id"],
                "adhoc_filters": [],
                "row_limit": 100
            }),
            description="Количество запросов по тенантам"
        )
        db.session.add(tenant_activity_chart)
        charts.append(tenant_activity_chart)
        
        # 4. Статистика чат-сессий
        chat_sessions_chart = Slice(
            slice_name="Статистика чат-сессий",
            datasource_type='table',
            datasource_id=chat_metrics_ds.id,
            viz_type='line',
            params=json.dumps({
                "metrics": [
                    {"expressionType": "SIMPLE", "column": {"column_name": "session_id", "type": "VARCHAR"}, "label": "Сессии", "optionName": "metric_1", "aggregate": "COUNT_DISTINCT"},
                    {"expressionType": "SIMPLE", "column": {"column_name": "messages_count", "type": "INTEGER"}, "label": "Сообщения", "optionName": "metric_2", "aggregate": "SUM"}
                ],
                "adhoc_filters": [],
                "row_limit": 1000,
                "x_axis": "timestamp",
                "y_axis": "metric_value"
            }),
            description="Статистика чат-сессий и сообщений"
        )
        db.session.add(chat_sessions_chart)
        charts.append(chat_sessions_chart)
        
        # 5. Успешность запросов
        success_rate_chart = Slice(
            slice_name="Успешность запросов",
            datasource_type='table',
            datasource_id=search_metrics_ds.id,
            viz_type='pie',
            params=json.dumps({
                "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "success", "type": "BOOLEAN"}, "label": "Количество", "optionName": "metric_1", "aggregate": "COUNT"}],
                "groupby": ["success"],
                "adhoc_filters": [],
                "row_limit": 100
            }),
            description="Распределение успешных и неуспешных запросов"
        )
        db.session.add(success_rate_chart)
        charts.append(success_rate_chart)
        
        db.session.commit()
        
        # Создаем дашборд
        dashboard = Dashboard(
            dashboard_title="Использование системы",
            slug="rag-usage-dashboard",
            position_json=json.dumps({
                "DASHBOARD_VERSION_KEY": "v2",
                "DASHBOARD_ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
                "GRID_ID": {
                    "id": "GRID_ID",
                    "type": "GRID",
                    "children": [
                        {"id": "CHART-1", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-2", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-3", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-4", "type": "CHART", "meta": {"width": 6, "height": 4}},
                        {"id": "CHART-5", "type": "CHART", "meta": {"width": 12, "height": 4}}
                    ]
                }
            }),
            css="",
            json_metadata=json.dumps({
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "color_scheme": None,
                "label_colors": {}
            }),
            slices=[chart.id for chart in charts],
            published=True
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        logger.info("Usage dashboard created successfully")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error creating usage dashboard: {e}")
        db.session.rollback()
        return None


def main():
    """Основная функция создания дашбордов"""
    logger.info("Starting dashboard creation for RAG platform...")
    
    try:
        # Создаем дашборды
        quality_dashboard = create_quality_dashboard()
        performance_dashboard = create_performance_dashboard()
        usage_dashboard = create_usage_dashboard()
        
        if all([quality_dashboard, performance_dashboard, usage_dashboard]):
            logger.info("All dashboards created successfully!")
            return True
        else:
            logger.error("Some dashboards failed to create")
            return False
        
    except Exception as e:
        logger.error(f"Error during dashboard creation: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
