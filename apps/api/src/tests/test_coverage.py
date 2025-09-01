"""
Тесты для проверки покрытия кода и качества тестов
"""
import pytest
import subprocess
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path


class TestCodeCoverage:
    """Тесты покрытия кода"""
    
    def test_minimum_coverage_threshold(self):
        """Тест минимального порога покрытия кода"""
        # Запускаем pytest с покрытием
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--cov=src", 
            "--cov-report=xml:coverage.xml",
            "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Проверяем что coverage.xml создан
        coverage_file = Path(__file__).parent.parent.parent / "coverage.xml"
        assert coverage_file.exists(), "Coverage report not generated"
        
        # Парсим XML отчет
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Извлекаем общее покрытие
        coverage_percent = float(root.attrib.get('line-rate', 0)) * 100
        
        print(f"Current code coverage: {coverage_percent:.1f}%")
        
        # Проверяем минимальный порог
        MINIMUM_COVERAGE = 80.0
        assert coverage_percent >= MINIMUM_COVERAGE, \
            f"Code coverage {coverage_percent:.1f}% below minimum {MINIMUM_COVERAGE}%"
    
    def test_branch_coverage_threshold(self):
        """Тест покрытия ветвлений"""
        coverage_file = Path(__file__).parent.parent.parent / "coverage.xml"
        
        if not coverage_file.exists():
            pytest.skip("Coverage report not found")
        
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Извлекаем покрытие ветвлений
        branch_coverage = float(root.attrib.get('branch-rate', 0)) * 100
        
        print(f"Current branch coverage: {branch_coverage:.1f}%")
        
        # Проверяем минимальный порог для ветвлений
        MINIMUM_BRANCH_COVERAGE = 70.0
        assert branch_coverage >= MINIMUM_BRANCH_COVERAGE, \
            f"Branch coverage {branch_coverage:.1f}% below minimum {MINIMUM_BRANCH_COVERAGE}%"
    
    def test_critical_modules_coverage(self):
        """Тест покрытия критически важных модулей"""
        coverage_file = Path(__file__).parent.parent.parent / "coverage.xml"
        
        if not coverage_file.exists():
            pytest.skip("Coverage report not found")
        
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Критически важные модули
        critical_modules = [
            'src/services/auth.py',
            'src/services/cache.py',
            'src/services/performance_monitor.py',
            'src/middleware/auth.py',
            'src/routers/auth.py'
        ]
        
        critical_coverage = {}
        
        # Находим покрытие для каждого критического модуля
        for package in root.findall('.//package'):
            for class_elem in package.findall('.//class'):
                filename = class_elem.attrib.get('filename', '')
                
                for critical_module in critical_modules:
                    if critical_module in filename:
                        line_rate = float(class_elem.attrib.get('line-rate', 0)) * 100
                        critical_coverage[critical_module] = line_rate
        
        # Проверяем покрытие критических модулей
        CRITICAL_MODULE_THRESHOLD = 90.0
        
        for module, coverage in critical_coverage.items():
            print(f"Critical module {module}: {coverage:.1f}% coverage")
            assert coverage >= CRITICAL_MODULE_THRESHOLD, \
                f"Critical module {module} has only {coverage:.1f}% coverage (min: {CRITICAL_MODULE_THRESHOLD}%)"
    
    def test_no_untested_modules(self):
        """Тест что нет модулей без тестов"""
        coverage_file = Path(__file__).parent.parent.parent / "coverage.xml"
        
        if not coverage_file.exists():
            pytest.skip("Coverage report not found")
        
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        untested_modules = []
        
        # Находим модули с нулевым покрытием
        for package in root.findall('.//package'):
            for class_elem in package.findall('.//class'):
                filename = class_elem.attrib.get('filename', '')
                line_rate = float(class_elem.attrib.get('line-rate', 0))
                
                # Игнорируем тестовые файлы и __init__.py
                if ('test_' not in filename and 
                    '__init__.py' not in filename and
                    'main.py' not in filename and
                    line_rate == 0.0):
                    untested_modules.append(filename)
        
        assert len(untested_modules) == 0, \
            f"Found untested modules: {', '.join(untested_modules)}"


class TestTestQuality:
    """Тесты качества самих тестов"""
    
    def test_test_count_by_category(self):
        """Тест количества тестов по категориям"""
        # Подсчитываем тесты по маркерам
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--collect-only", "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Простой подсчет строк с тестами
        test_lines = [line for line in result.stdout.split('\n') if 'test_' in line]
        total_tests = len(test_lines)
        
        print(f"Total tests found: {total_tests}")
        
        # Минимальные требования к количеству тестов
        MINIMUM_TOTAL_TESTS = 50
        assert total_tests >= MINIMUM_TOTAL_TESTS, \
            f"Found only {total_tests} tests, minimum required: {MINIMUM_TOTAL_TESTS}"
    
    def test_unit_tests_coverage(self):
        """Тест покрытия unit тестами"""
        # Запускаем только unit тесты
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "unit",
            "--cov=src",
            "--cov-report=term-missing",
            "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Извлекаем покрытие из вывода
        output_lines = result.stdout.split('\n')
        coverage_line = None
        
        for line in output_lines:
            if 'TOTAL' in line and '%' in line:
                coverage_line = line
                break
        
        if coverage_line:
            # Извлекаем процент покрытия
            coverage_percent = float(coverage_line.split()[-1].rstrip('%'))
            print(f"Unit tests coverage: {coverage_percent:.1f}%")
            
            # Unit тесты должны покрывать основную логику
            UNIT_TESTS_COVERAGE = 60.0
            assert coverage_percent >= UNIT_TESTS_COVERAGE, \
                f"Unit tests coverage {coverage_percent:.1f}% below {UNIT_TESTS_COVERAGE}%"
    
    def test_integration_tests_exist(self):
        """Тест наличия integration тестов"""
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "integration",
            "--collect-only", "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        integration_test_lines = [line for line in result.stdout.split('\n') if 'test_' in line]
        integration_tests_count = len(integration_test_lines)
        
        print(f"Integration tests found: {integration_tests_count}")
        
        MINIMUM_INTEGRATION_TESTS = 10
        assert integration_tests_count >= MINIMUM_INTEGRATION_TESTS, \
            f"Found only {integration_tests_count} integration tests, minimum: {MINIMUM_INTEGRATION_TESTS}"
    
    def test_e2e_tests_exist(self):
        """Тест наличия E2E тестов"""
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "e2e",
            "--collect-only", "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        e2e_test_lines = [line for line in result.stdout.split('\n') if 'test_' in line]
        e2e_tests_count = len(e2e_test_lines)
        
        print(f"E2E tests found: {e2e_tests_count}")
        
        MINIMUM_E2E_TESTS = 5
        assert e2e_tests_count >= MINIMUM_E2E_TESTS, \
            f"Found only {e2e_tests_count} E2E tests, minimum: {MINIMUM_E2E_TESTS}"
    
    def test_load_tests_exist(self):
        """Тест наличия нагрузочных тестов"""
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "load",
            "--collect-only", "--quiet"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        load_test_lines = [line for line in result.stdout.split('\n') if 'test_' in line]
        load_tests_count = len(load_test_lines)
        
        print(f"Load tests found: {load_tests_count}")
        
        MINIMUM_LOAD_TESTS = 3
        assert load_tests_count >= MINIMUM_LOAD_TESTS, \
            f"Found only {load_tests_count} load tests, minimum: {MINIMUM_LOAD_TESTS}"


class TestTestPerformance:
    """Тесты производительности самих тестов"""
    
    def test_unit_tests_performance(self):
        """Тест производительности unit тестов"""
        import time
        
        start_time = time.time()
        
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "unit",
            "--quiet",
            "--tb=no"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        execution_time = time.time() - start_time
        
        print(f"Unit tests execution time: {execution_time:.2f}s")
        
        # Unit тесты должны выполняться быстро
        MAX_UNIT_TESTS_TIME = 30.0  # 30 секунд
        assert execution_time <= MAX_UNIT_TESTS_TIME, \
            f"Unit tests took {execution_time:.2f}s, maximum allowed: {MAX_UNIT_TESTS_TIME}s"
        
        # Проверяем что тесты прошли успешно
        assert result.returncode == 0, f"Unit tests failed: {result.stdout}"
    
    def test_test_isolation(self):
        """Тест изоляции тестов (повторный запуск должен давать тот же результат)"""
        # Запускаем тесты дважды
        results = []
        
        for run in range(2):
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "-m", "unit",
                "--quiet",
                "--tb=no"
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
            
            results.append(result.returncode)
        
        # Результаты должны быть одинаковыми
        assert results[0] == results[1], \
            "Test results differ between runs - tests are not properly isolated"
    
    def test_no_test_dependencies(self):
        """Тест отсутствия зависимостей между тестами"""
        # Запускаем тесты в случайном порядке
        result_random = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "unit",
            "--random-order",
            "--quiet",
            "--tb=no"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Запускаем тесты в обычном порядке
        result_normal = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-m", "unit", 
            "--quiet",
            "--tb=no"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Результаты должны быть одинаковыми
        assert result_random.returncode == result_normal.returncode, \
            "Test results differ when run in random order - tests have dependencies"


class TestTestDocumentation:
    """Тесты документации тестов"""
    
    def test_test_functions_have_docstrings(self):
        """Тест наличия docstring у тестовых функций"""
        import ast
        import os
        
        test_files = []
        test_dir = Path(__file__).parent
        
        # Собираем все тестовые файлы
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        
        undocumented_tests = []
        
        # Проверяем каждый тестовый файл
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                # Ищем тестовые функции без docstring
                for node in ast.walk(tree):
                    if (isinstance(node, ast.FunctionDef) and 
                        node.name.startswith('test_') and
                        not ast.get_docstring(node)):
                        undocumented_tests.append(f"{test_file.name}::{node.name}")
            
            except Exception as e:
                print(f"Error parsing {test_file}: {e}")
        
        # Допускаем некоторое количество недокументированных тестов
        MAX_UNDOCUMENTED_TESTS = 5
        assert len(undocumented_tests) <= MAX_UNDOCUMENTED_TESTS, \
            f"Found {len(undocumented_tests)} undocumented test functions: {undocumented_tests[:10]}"
    
    def test_test_classes_have_docstrings(self):
        """Тест наличия docstring у тестовых классов"""
        import ast
        import os
        
        test_files = []
        test_dir = Path(__file__).parent
        
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        
        undocumented_classes = []
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if (isinstance(node, ast.ClassDef) and 
                        node.name.startswith('Test') and
                        not ast.get_docstring(node)):
                        undocumented_classes.append(f"{test_file.name}::{node.name}")
            
            except Exception as e:
                print(f"Error parsing {test_file}: {e}")
        
        # Все тестовые классы должны быть документированы
        assert len(undocumented_classes) == 0, \
            f"Found undocumented test classes: {undocumented_classes}"
