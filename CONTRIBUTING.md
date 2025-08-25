# 🤝 Вклад в проект

Спасибо за интерес к RAG Platform! Мы приветствуем любой вклад в развитие проекта.

## 🚀 Как начать

### 1. Fork и клонирование
```bash
# Fork репозитория на GitHub
# Затем клонируйте ваш fork
git clone https://github.com/YOUR_USERNAME/Curproject01.git
cd Curproject01

# Добавьте upstream
git remote add upstream https://github.com/ORIGINAL_OWNER/Curproject01.git
```

### 2. Создание ветки
```bash
# Создайте новую ветку для ваших изменений
git checkout -b feature/amazing-feature
# или
git checkout -b bugfix/fix-issue-123
```

### 3. Внесение изменений
```bash
# Внесите изменения в код
# Добавьте тесты
# Обновите документацию

# Проверьте код
make lint
make test

# Зафиксируйте изменения
git add .
git commit -m "feat: add amazing feature"
```

### 4. Push и Pull Request
```bash
# Отправьте изменения
git push origin feature/amazing-feature

# Создайте Pull Request на GitHub
```

## 📋 Стандарты кода

### Python
- **Стиль**: PEP 8, Black, Ruff
- **Типизация**: Type hints для всех функций
- **Документация**: Docstrings для всех классов и методов
- **Тесты**: Покрытие не менее 80%

### Commit сообщения
Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new search functionality
fix: resolve memory leak in vector store
docs: update API documentation
test: add unit tests for chat service
refactor: simplify document parser
style: format code with black
perf: optimize embedding generation
```

### Структура PR
```markdown
## Описание
Краткое описание изменений

## Тип изменения
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Тестирование
- [ ] Unit tests пройдены
- [ ] Integration tests пройдены
- [ ] Manual testing выполнен

## Чеклист
- [ ] Код соответствует стандартам
- [ ] Добавлены тесты
- [ ] Обновлена документация
- [ ] Изменения протестированы локально
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
make test

# Тесты API
make test-api

# Тесты Streamlit
make test-streamlit

# С покрытием
cd apps/api && python -m pytest --cov=src tests/
```

### Написание тестов
```python
# tests/test_search.py
import pytest
from src.services.search import SearchService

class TestSearchService:
    @pytest.fixture
    def search_service(self):
        return SearchService()
    
    def test_search_documents(self, search_service):
        results = search_service.search("test query")
        assert len(results) > 0
        assert all(r.score > 0 for r in results)
```

## 📚 Документация

### Обновление README
- Добавляйте новые функции
- Обновляйте примеры
- Исправляйте ошибки

### API документация
- Обновляйте схемы Pydantic
- Добавляйте описания эндпоинтов
- Примеры запросов и ответов

### Комментарии в коде
```python
def process_document(file_path: str) -> Document:
    """
    Обрабатывает документ и извлекает текст.
    
    Args:
        file_path: Путь к файлу документа
        
    Returns:
        Document: Обработанный документ с извлеченным текстом
        
    Raises:
        FileNotFoundError: Если файл не найден
        UnsupportedFormatError: Если формат не поддерживается
    """
    pass
```

## 🔧 Разработка

### Локальная разработка
```bash
# Запуск в режиме разработки
make dev

# Остановка
make dev-stop

# Проверка здоровья
make health
```

### Отладка
```bash
# Логи API
make logs-api

# Логи Streamlit
make logs-streamlit

# Shell в контейнер
make shell-api
```

### Линтинг и форматирование
```bash
# Проверка кода
make lint

# Форматирование
make format

# Автоматическое исправление
cd apps/api && ruff check --fix src/
```

## 🐛 Отчеты об ошибках

### Создание Issue
```markdown
## Описание ошибки
Четкое описание проблемы

## Шаги для воспроизведения
1. Откройте страницу X
2. Нажмите кнопку Y
3. Ошибка происходит в Z

## Ожидаемое поведение
Что должно происходить

## Фактическое поведение
Что происходит на самом деле

## Окружение
- ОС: Ubuntu 22.04
- Python: 3.11.5
- Docker: 24.0.5

## Логи
```
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    main()
```
```

## 💡 Предложения новых функций

### Создание Feature Request
```markdown
## Описание функции
Подробное описание новой функциональности

## Проблема
Какую проблему решает эта функция

## Предлагаемое решение
Как должна работать функция

## Альтернативы
Какие еще решения возможны

## Дополнительная информация
Скриншоты, примеры, ссылки
```

## 🏷️ Версионирование

Мы используем [Semantic Versioning](https://semver.org/):

- **MAJOR**: Несовместимые изменения API
- **MINOR**: Новая функциональность (совместимая)
- **PATCH**: Исправления ошибок (совместимые)

## 📞 Получение помощи

### Общение
- **Issues**: Для багов и feature requests
- **Discussions**: Для вопросов и обсуждений
- **Wiki**: Для документации

### Комьюнити
- Присоединяйтесь к обсуждениям
- Помогайте другим участникам
- Делитесь опытом использования

## 🎉 Признание

Все участники будут добавлены в:
- CONTRIBUTORS.md файл
- README.md (если значительный вклад)
- Release notes

## 📄 Лицензия

Внося изменения, вы соглашаетесь с тем, что ваш вклад будет лицензирован под MIT License.

---

Спасибо за ваш вклад в RAG Platform! 🚀
