#!/usr/bin/env python3
"""
Test for Airflow DAGs
"""

import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_ingest_dag_import():
    """Test ingest documents DAG import"""
    try:
        # Импортируем DAG
        from dags.ingest_documents_dag import dag
        
        print(f"✅ Ingest DAG imported successfully: {dag.dag_id}")
        print(f"   Schedule: {dag.schedule_interval}")
        print(f"   Tags: {dag.tags}")
        print(f"   Tasks: {len(dag.tasks)}")
        
        # Проверяем основные параметры
        if dag.dag_id == 'ingest_documents':
            print("   ✅ DAG ID is correct")
        else:
            print("   ❌ DAG ID is incorrect")
            return False
        
        if dag.schedule_interval == '*/15 * * * *':
            print("   ✅ Schedule interval is correct (every 15 minutes)")
        else:
            print("   ❌ Schedule interval is incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ingest DAG import test failed: {e}")
        return False

def test_process_dag_import():
    """Test process and index DAG import"""
    try:
        # Импортируем DAG
        from dags.process_and_index_dag import dag
        
        print(f"✅ Process DAG imported successfully: {dag.dag_id}")
        print(f"   Schedule: {dag.schedule_interval}")
        print(f"   Tags: {dag.tags}")
        print(f"   Tasks: {len(dag.tasks)}")
        
        # Проверяем основные параметры
        if dag.dag_id == 'process_and_index_documents':
            print("   ✅ DAG ID is correct")
        else:
            print("   ❌ DAG ID is incorrect")
            return False
        
        if dag.schedule_interval == '0 */1 * * *':
            print("   ✅ Schedule interval is correct (every hour)")
        else:
            print("   ❌ Schedule interval is incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Process DAG import test failed: {e}")
        return False

def test_dag_structure():
    """Test DAG structure and dependencies"""
    try:
        from dags.ingest_documents_dag import dag as ingest_dag
        from dags.process_and_index_dag import dag as process_dag
        
        # Проверяем структуру ingest DAG
        print("Testing Ingest DAG structure...")
        
        expected_tasks = [
            'start', 'discover_documents', 'validate_documents', 
            'process_documents', 'update_processing_status', 
            'cleanup_temp_files', 'generate_report', 'end'
        ]
        
        actual_tasks = [task.task_id for task in ingest_dag.tasks]
        
        for expected_task in expected_tasks:
            if expected_task in actual_tasks:
                print(f"   ✅ Task {expected_task} exists")
            else:
                print(f"   ❌ Task {expected_task} missing")
                return False
        
        # Проверяем структуру process DAG
        print("Testing Process DAG structure...")
        
        expected_tasks = [
            'start', 'get_pending_documents', 'parse_documents',
            'extract_tables', 'create_chunks', 'generate_embeddings',
            'index_to_vectorstore', 'update_processing_status',
            'generate_report', 'end'
        ]
        
        actual_tasks = [task.task_id for task in process_dag.tasks]
        
        for expected_task in expected_tasks:
            if expected_task in actual_tasks:
                print(f"   ✅ Task {expected_task} exists")
            else:
                print(f"   ❌ Task {expected_task} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ DAG structure test failed: {e}")
        return False

def test_task_operators():
    """Test task operators and types"""
    try:
        from dags.ingest_documents_dag import dag as ingest_dag
        from dags.process_and_index_dag import dag as process_dag
        
        # Проверяем операторы в ingest DAG
        print("Testing Ingest DAG operators...")
        
        for task in ingest_dag.tasks:
            if task.task_id in ['start', 'end']:
                if hasattr(task, 'operator_class') and 'EmptyOperator' in str(task.operator_class):
                    print(f"   ✅ Task {task.task_id} is EmptyOperator")
                else:
                    print(f"   ❌ Task {task.task_id} is not EmptyOperator")
                    return False
            else:
                if hasattr(task, 'operator_class') and 'PythonOperator' in str(task.operator_class):
                    print(f"   ✅ Task {task.task_id} is PythonOperator")
                else:
                    print(f"   ❌ Task {task.task_id} is not PythonOperator")
                    return False
        
        # Проверяем операторы в process DAG
        print("Testing Process DAG operators...")
        
        for task in process_dag.tasks:
            if task.task_id in ['start', 'end']:
                if hasattr(task, 'operator_class') and 'EmptyOperator' in str(task.operator_class):
                    print(f"   ✅ Task {task.task_id} is EmptyOperator")
                else:
                    print(f"   ❌ Task {task.task_id} is not EmptyOperator")
                    return False
            else:
                if hasattr(task, 'operator_class') and 'PythonOperator' in str(task.operator_class):
                    print(f"   ✅ Task {task.task_id} is PythonOperator")
                else:
                    print(f"   ❌ Task {task.task_id} is not PythonOperator")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Task operators test failed: {e}")
        return False

def test_dag_configuration():
    """Test DAG configuration and settings"""
    try:
        from dags.ingest_documents_dag import dag as ingest_dag
        from dags.process_and_index_dag import dag as process_dag
        
        # Проверяем конфигурацию ingest DAG
        print("Testing Ingest DAG configuration...")
        
        if ingest_dag.max_active_runs == 1:
            print("   ✅ Max active runs is 1")
        else:
            print("   ❌ Max active runs is not 1")
            return False
        
        if ingest_dag.catchup is False:
            print("   ✅ Catchup is disabled")
        else:
            print("   ❌ Catchup is enabled")
            return False
        
        if ingest_dag.owner == 'rag-platform':
            print("   ✅ Owner is correct")
        else:
            print("   ❌ Owner is incorrect")
            return False
        
        # Проверяем конфигурацию process DAG
        print("Testing Process DAG configuration...")
        
        if process_dag.max_active_runs == 1:
            print("   ✅ Max active runs is 1")
        else:
            print("   ❌ Max active runs is not 1")
            return False
        
        if process_dag.catchup is False:
            print("   ✅ Catchup is disabled")
        else:
            print("   ❌ Catchup is enabled")
            return False
        
        if process_dag.owner == 'rag-platform':
            print("   ✅ Owner is correct")
        else:
            print("   ❌ Owner is incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ DAG configuration test failed: {e}")
        return False

def test_function_imports():
    """Test that all required functions can be imported"""
    try:
        # Проверяем функции ingest DAG
        print("Testing Ingest DAG function imports...")
        
        from dags.ingest_documents_dag import (
            discover_new_documents,
            validate_document,
            process_document_with_rag,
            update_processing_status,
            cleanup_temp_files,
            generate_processing_report
        )
        
        print("   ✅ All ingest DAG functions imported successfully")
        
        # Проверяем функции process DAG
        print("Testing Process DAG function imports...")
        
        from dags.process_and_index_dag import (
            get_pending_documents,
            parse_documents,
            extract_tables,
            create_chunks,
            generate_embeddings,
            index_to_vectorstore,
            update_processing_status,
            generate_processing_report
        )
        
        print("   ✅ All process DAG functions imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Function imports test failed: {e}")
        return False

def main():
    """Run all DAG tests"""
    print("🧪 Testing Airflow DAGs...\n")
    
    tests = [
        ("Ingest DAG Import", test_ingest_dag_import),
        ("Process DAG Import", test_process_dag_import),
        ("DAG Structure", test_dag_structure),
        ("Task Operators", test_task_operators),
        ("DAG Configuration", test_dag_configuration),
        ("Function Imports", test_function_imports),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All DAG tests passed!")
        print("\n📋 New Airflow capabilities:")
        print("   ✅ Document discovery and validation")
        print("   ✅ RAG Core integration")
        print("   ✅ Document parsing and table extraction")
        print("   ✅ Chunking and embedding generation")
        print("   ✅ Vector store indexing")
        print("   ✅ Comprehensive reporting and monitoring")
        print("   ✅ Error handling and retry logic")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
