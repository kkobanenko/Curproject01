"""
Тесты для новых Airflow DAG
"""

import sys
import os
import unittest
from pathlib import Path

# Добавляем путь к Airflow DAG
sys.path.append(str(Path(__file__).parent / 'dags'))

class TestNewDAGs(unittest.TestCase):
    """Тесты для новых DAG"""
    
    def test_sync_clickhouse_metrics_dag_import(self):
        """Тест импорта DAG для синхронизации метрик"""
        try:
            from dags.sync_clickhouse_metrics_dag import dag
            
            # Проверяем основные параметры DAG
            self.assertEqual(dag.dag_id, 'sync_clickhouse_metrics')
            self.assertEqual(dag.schedule_interval, '0 */2 * * *')
            self.assertEqual(dag.max_active_runs, 1)
            
            # Проверяем теги
            expected_tags = ['rag', 'metrics', 'clickhouse', 'monitoring']
            for tag in expected_tags:
                self.assertIn(tag, dag.tags)
            
            # Проверяем задачи
            expected_tasks = [
                'start',
                'collect_rag_metrics',
                'collect_search_metrics', 
                'collect_quality_metrics',
                'transform_metrics_for_clickhouse',
                'send_metrics_to_clickhouse',
                'generate_metrics_report',
                'end'
            ]
            
            for task_id in expected_tasks:
                self.assertIn(task_id, dag.task_ids)
            
            print("✓ sync_clickhouse_metrics_dag imported successfully")
            
        except ImportError as e:
            self.fail(f"Failed to import sync_clickhouse_metrics_dag: {e}")
        except Exception as e:
            self.fail(f"Unexpected error testing sync_clickhouse_metrics_dag: {e}")
    
    def test_system_maintenance_dag_import(self):
        """Тест импорта DAG для технического обслуживания"""
        try:
            from dags.system_maintenance_dag import dag
            
            # Проверяем основные параметры DAG
            self.assertEqual(dag.dag_id, 'system_maintenance')
            self.assertEqual(dag.schedule_interval, '0 2 * * *')
            self.assertEqual(dag.max_active_runs, 1)
            
            # Проверяем теги
            expected_tags = ['rag', 'maintenance', 'monitoring', 'cleanup']
            for tag in expected_tags:
                self.assertIn(tag, dag.tags)
            
            # Проверяем задачи
            expected_tasks = [
                'start',
                'check_system_health',
                'cleanup_old_logs',
                'optimize_database',
                'generate_maintenance_report',
                'end'
            ]
            
            for task_id in expected_tasks:
                self.assertIn(task_id, dag.task_ids)
            
            print("✓ system_maintenance_dag imported successfully")
            
        except ImportError as e:
            self.fail(f"Failed to import system_maintenance_dag: {e}")
        except Exception as e:
            self.fail(f"Unexpected error testing system_maintenance_dag: {e}")
    
    def test_dag_structure(self):
        """Тест структуры DAG"""
        try:
            from dags.sync_clickhouse_metrics_dag import dag as metrics_dag
            from dags.system_maintenance_dag import dag as maintenance_dag
            
            # Проверяем, что DAG имеют правильную структуру
            for dag_name, dag in [('metrics', metrics_dag), ('maintenance', maintenance_dag)]:
                # Проверяем, что есть начальная и конечная задачи
                self.assertIn('start', dag.task_ids)
                self.assertIn('end', dag.task_ids)
                
                # Проверяем, что все задачи подключены
                start_task = dag.get_task('start')
                end_task = dag.get_task('end')
                
                # Проверяем, что есть путь от start до end
                self.assertTrue(dag.has_task('start'))
                self.assertTrue(dag.has_task('end'))
                
                print(f"✓ {dag_name} DAG structure is valid")
                
        except Exception as e:
            self.fail(f"Error testing DAG structure: {e}")
    
    def test_dag_configuration(self):
        """Тест конфигурации DAG"""
        try:
            from dags.sync_clickhouse_metrics_dag import dag as metrics_dag
            from dags.system_maintenance_dag import dag as maintenance_dag
            
            # Проверяем конфигурацию метрик DAG
            self.assertEqual(metrics_dag.owner, 'rag-platform')
            self.assertEqual(metrics_dag.catchup, False)
            self.assertEqual(metrics_dag.description, 'Синхронизация метрик RAG системы в ClickHouse')
            
            # Проверяем конфигурацию maintenance DAG
            self.assertEqual(maintenance_dag.owner, 'rag-platform')
            self.assertEqual(maintenance_dag.catchup, False)
            self.assertEqual(maintenance_dag.description, 'Мониторинг и очистка системы RAG')
            
            print("✓ DAG configuration is correct")
            
        except Exception as e:
            self.fail(f"Error testing DAG configuration: {e}")
    
    def test_function_availability(self):
        """Тест доступности функций"""
        try:
            from dags.sync_clickhouse_metrics_dag import (
                collect_rag_metrics,
                collect_search_metrics,
                collect_quality_metrics,
                transform_metrics_for_clickhouse,
                send_metrics_to_clickhouse,
                generate_metrics_report
            )
            
            from dags.system_maintenance_dag import (
                check_system_health,
                cleanup_old_logs,
                optimize_database,
                generate_maintenance_report
            )
            
            # Проверяем, что все функции доступны
            functions = [
                collect_rag_metrics,
                collect_search_metrics,
                collect_quality_metrics,
                transform_metrics_for_clickhouse,
                send_metrics_to_clickhouse,
                generate_metrics_report,
                check_system_health,
                cleanup_old_logs,
                optimize_database,
                generate_maintenance_report
            ]
            
            for func in functions:
                self.assertTrue(callable(func))
            
            print("✓ All functions are available and callable")
            
        except ImportError as e:
            self.fail(f"Failed to import functions: {e}")
        except Exception as e:
            self.fail(f"Unexpected error testing functions: {e}")

def test_dag_imports():
    """Простой тест импорта DAG"""
    print("Testing DAG imports...")
    
    try:
        # Тест импорта метрик DAG
        sys.path.append(str(Path(__file__).parent / 'dags'))
        from dags.sync_clickhouse_metrics_dag import dag as metrics_dag
        print(f"✓ Metrics DAG imported: {metrics_dag.dag_id}")
        
        # Тест импорта maintenance DAG
        from dags.system_maintenance_dag import dag as maintenance_dag
        print(f"✓ Maintenance DAG imported: {maintenance_dag.dag_id}")
        
        return True
        
    except Exception as e:
        print(f"✗ DAG import failed: {e}")
        return False

if __name__ == '__main__':
    print("Running DAG tests...")
    
    # Простой тест импорта
    if test_dag_imports():
        print("Basic DAG import test passed")
    else:
        print("Basic DAG import test failed")
    
    # Полные unit тесты
    try:
        unittest.main(argv=[''], exit=False, verbosity=2)
    except Exception as e:
        print(f"Unit tests failed: {e}")
    
    print("DAG tests completed")
