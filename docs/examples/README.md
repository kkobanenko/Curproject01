# 💡 Примеры использования RAG Platform

## 🌟 Введение

Эта документация содержит практические примеры использования RAG Platform для различных сценариев и отраслей. Каждый пример включает готовый код, пошаговые инструкции и рекомендации по оптимизации.

## 📖 Содержание

1. [🏢 Корпоративный поиск знаний](#-корпоративный-поиск-знаний)
2. [📚 Электронная библиотека](#-электронная-библиотека)
3. [🏥 Медицинская документация](#-медицинская-документация)
4. [⚖️ Правовые документы](#-правовые-документы)
5. [🔬 Научные исследования](#-научные-исследования)
6. [🏭 Техническая документация](#-техническая-документация)
7. [📊 Бизнес-аналитика](#-бизнес-аналитика)
8. [🎓 Образовательная платформа](#-образовательная-платформа)

## 🏢 Корпоративный поиск знаний

### Сценарий
Компания хочет создать единую базу знаний для сотрудников, включающую:
- Внутренние процедуры и политики
- Техническую документацию
- Отчеты и аналитику
- FAQ и базу знаний поддержки

### Пример реализации

#### 1. Настройка структуры документов
```python
import requests
import os
from pathlib import Path

class CorporateKnowledgeBase:
    def __init__(self, api_base_url, admin_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {admin_token}"}
    
    def setup_document_categories(self):
        """Настройка категорий документов для корпоративного использования"""
        categories = {
            "policies": {
                "name": "Политики и процедуры",
                "tags": ["политика", "процедура", "регламент"],
                "description": "Внутренние документы компании"
            },
            "technical": {
                "name": "Техническая документация", 
                "tags": ["техническая", "инструкция", "руководство"],
                "description": "Техническая и пользовательская документация"
            },
            "analytics": {
                "name": "Отчеты и аналитика",
                "tags": ["отчет", "аналитика", "метрики"],
                "description": "Бизнес-отчеты и аналитические материалы"
            },
            "support": {
                "name": "База знаний поддержки",
                "tags": ["FAQ", "поддержка", "решение"],
                "description": "Часто задаваемые вопросы и решения"
            }
        }
        return categories
    
    def bulk_upload_documents(self, documents_folder):
        """Массовая загрузка документов с автоматической категоризацией"""
        results = []
        
        for root, dirs, files in os.walk(documents_folder):
            category = Path(root).name.lower()
            
            for file in files:
                if file.lower().endswith(('.pdf', '.docx', '.txt', '.html')):
                    file_path = os.path.join(root, file)
                    
                    # Определение тегов на основе пути
                    tags = self._determine_tags(file_path, category)
                    
                    try:
                        result = self.upload_document(file_path, tags, category)
                        results.append({
                            "file": file,
                            "status": "success",
                            "document_id": result.get("document", {}).get("id")
                        })
                    except Exception as e:
                        results.append({
                            "file": file,
                            "status": "error", 
                            "error": str(e)
                        })
        
        return results
    
    def upload_document(self, file_path, tags, category):
        """Загрузка отдельного документа"""
        with open(file_path, 'rb') as file:
            files = {"file": file}
            data = {
                "tags": tags,
                "metadata": {
                    "category": category,
                    "upload_source": "bulk_import",
                    "department": self._extract_department(file_path)
                }
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/documents",
                headers=self.headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    def _determine_tags(self, file_path, category):
        """Автоматическое определение тегов на основе пути и содержимого"""
        tags = [category]
        
        path_lower = file_path.lower()
        
        # Теги на основе пути
        if "hr" in path_lower or "кадры" in path_lower:
            tags.extend(["HR", "кадры"])
        elif "it" in path_lower or "ИТ" in path_lower:
            tags.extend(["IT", "технологии"])
        elif "finance" in path_lower or "финансы" in path_lower:
            tags.extend(["финансы", "бухгалтерия"])
        elif "legal" in path_lower or "правовые" in path_lower:
            tags.extend(["юридические", "правовые"])
        
        # Теги на основе типа файла
        if "policy" in path_lower or "политика" in path_lower:
            tags.append("политика")
        elif "procedure" in path_lower or "процедура" in path_lower:
            tags.append("процедура")
        elif "manual" in path_lower or "руководство" in path_lower:
            tags.append("руководство")
        
        return tags
    
    def _extract_department(self, file_path):
        """Извлечение отдела из пути файла"""
        path_parts = Path(file_path).parts
        departments = {
            "hr": "Отдел кадров",
            "it": "IT отдел", 
            "finance": "Финансовый отдел",
            "legal": "Юридический отдел",
            "marketing": "Отдел маркетинга",
            "sales": "Отдел продаж"
        }
        
        for part in path_parts:
            part_lower = part.lower()
            for key, value in departments.items():
                if key in part_lower:
                    return value
        
        return "Общий"

# Пример использования
kb = CorporateKnowledgeBase(
    api_base_url="https://api.rag-platform.com",
    admin_token="YOUR_ADMIN_TOKEN"
)

# Загрузка документов
results = kb.bulk_upload_documents("/path/to/corporate/documents/")

# Анализ результатов
successful = [r for r in results if r["status"] == "success"]
failed = [r for r in results if r["status"] == "error"]

print(f"Успешно загружено: {len(successful)} документов")
print(f"Ошибки загрузки: {len(failed)} документов")
```

#### 2. Интеллектуальный поиск по корпоративной базе
```python
class CorporateSearch:
    def __init__(self, api_base_url, user_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {user_token}"}
    
    def search_policies(self, query, department=None):
        """Поиск в политиках и процедурах"""
        filters = {
            "tags": ["политика", "процедура", "регламент"]
        }
        
        if department:
            filters["metadata.department"] = department
        
        return self._semantic_search(query, filters)
    
    def search_technical_docs(self, query, technology=None):
        """Поиск в технической документации"""
        filters = {
            "tags": ["техническая", "инструкция", "руководство"]
        }
        
        if technology:
            filters["tags"].append(technology)
        
        return self._semantic_search(query, filters)
    
    def search_support_knowledge(self, query):
        """Поиск в базе знаний поддержки"""
        filters = {
            "tags": ["FAQ", "поддержка", "решение"]
        }
        
        return self._semantic_search(query, filters)
    
    def get_department_analytics(self, department, date_from=None, date_to=None):
        """Поиск аналитических отчетов по отделу"""
        filters = {
            "tags": ["отчет", "аналитика"],
            "metadata.department": department
        }
        
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        return self._semantic_search(f"отчет {department}", filters)
    
    def _semantic_search(self, query, filters):
        """Базовый семантический поиск"""
        search_data = {
            "query": query,
            "limit": 20,
            "threshold": 0.7,
            "filters": filters
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/search/semantic",
            headers=self.headers,
            json=search_data
        )
        response.raise_for_status()
        return response.json()
    
    def get_smart_answer(self, question, context_filters=None):
        """Получение интеллектуального ответа на вопрос"""
        rag_request = {
            "question": question,
            "context_limit": 8,
            "include_sources": True,
            "filters": context_filters or {},
            "model_params": {
                "temperature": 0.3,  # Более точные ответы для корпоративного контекста
                "max_tokens": 800
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        response.raise_for_status()
        return response.json()

# Примеры использования корпоративного поиска
search = CorporateSearch(
    api_base_url="https://api.rag-platform.com",
    user_token="USER_TOKEN"
)

# Поиск политик по отпускам
vacation_policies = search.search_policies(
    "политика отпусков и больничных",
    department="Отдел кадров"
)

# Поиск технической документации по API
api_docs = search.search_technical_docs(
    "REST API интеграция и авторизация",
    technology="API"
)

# Получение ответа на вопрос о процедурах
answer = search.get_smart_answer(
    "Как оформить командировку в другой город?",
    context_filters={"tags": ["командировка", "процедура"]}
)

print("Ответ:", answer["answer"])
print("Источники:", [s["document_title"] for s in answer["sources"]])
```

#### 3. Интеграция с корпоративными системами
```python
class CorporateIntegration:
    def __init__(self, rag_api_url, corp_systems_config):
        self.rag_api = rag_api_url
        self.corp_config = corp_systems_config
    
    def sync_with_sharepoint(self, sharepoint_site, library_name):
        """Синхронизация с SharePoint"""
        try:
            from office365.runtime.auth.authentication_context import AuthenticationContext
            from office365.sharepoint.client_context import ClientContext
            
            # Подключение к SharePoint
            auth_context = AuthenticationContext(url=sharepoint_site)
            auth_context.acquire_token_for_user(
                username=self.corp_config["sharepoint"]["username"],
                password=self.corp_config["sharepoint"]["password"]
            )
            
            ctx = ClientContext(sharepoint_site, auth_context)
            
            # Получение списка файлов
            library = ctx.web.lists.get_by_title(library_name)
            items = library.items.get().execute_query()
            
            # Синхронизация файлов
            for item in items:
                if item.file_system_object_type == 0:  # Файл
                    file_info = {
                        "name": item.properties["FileLeafRef"],
                        "url": item.properties["FileRef"],
                        "modified": item.properties["Modified"],
                        "size": item.properties.get("File_x0020_Size", 0)
                    }
                    
                    # Проверка необходимости обновления
                    if self._should_update_file(file_info):
                        self._download_and_upload_file(ctx, file_info)
            
            return {"status": "success", "synced_files": len(items)}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def sync_with_confluence(self, confluence_base_url, space_key):
        """Синхронизация с Confluence"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            auth = (
                self.corp_config["confluence"]["username"],
                self.corp_config["confluence"]["api_token"]
            )
            
            # Получение страниц из Confluence
            url = f"{confluence_base_url}/rest/api/content"
            params = {
                "spaceKey": space_key,
                "expand": "body.storage,version",
                "limit": 100
            }
            
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()
            
            pages = response.json()["results"]
            
            for page in pages:
                # Конвертация HTML в текст
                soup = BeautifulSoup(page["body"]["storage"]["value"], "html.parser")
                text_content = soup.get_text()
                
                # Создание документа в RAG Platform
                doc_data = {
                    "title": page["title"],
                    "content": text_content,
                    "source": "confluence",
                    "source_id": page["id"],
                    "tags": ["confluence", space_key],
                    "metadata": {
                        "space": space_key,
                        "version": page["version"]["number"],
                        "confluence_url": f"{confluence_base_url}/pages/viewpage.action?pageId={page['id']}"
                    }
                }
                
                self._create_or_update_document(doc_data)
            
            return {"status": "success", "synced_pages": len(pages)}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def setup_webhook_notifications(self):
        """Настройка webhook уведомлений для интеграции"""
        webhook_config = {
            "name": "Corporate Systems Integration",
            "url": self.corp_config["webhook_url"],
            "events": [
                "document.uploaded",
                "document.processed", 
                "search.performed",
                "user.registered"
            ],
            "active": True,
            "filters": {
                "tags": ["важно", "срочно"]  # Только важные события
            }
        }
        
        response = requests.post(
            f"{self.rag_api}/api/v1/webhooks/",
            headers={"Authorization": f"Bearer {self.corp_config['admin_token']}"},
            json=webhook_config
        )
        return response.json()

# Настройка интеграции
corp_config = {
    "sharepoint": {
        "username": "service@company.com",
        "password": "service_password"
    },
    "confluence": {
        "username": "service@company.com", 
        "api_token": "confluence_api_token"
    },
    "webhook_url": "https://company.com/rag-webhook",
    "admin_token": "ADMIN_TOKEN"
}

integration = CorporateIntegration(
    rag_api_url="https://api.rag-platform.com",
    corp_systems_config=corp_config
)

# Синхронизация с SharePoint
sharepoint_result = integration.sync_with_sharepoint(
    "https://company.sharepoint.com/sites/knowledge",
    "Documents"
)

# Синхронизация с Confluence
confluence_result = integration.sync_with_confluence(
    "https://company.atlassian.net/wiki",
    "CORP"
)

print("SharePoint sync:", sharepoint_result)
print("Confluence sync:", confluence_result)
```

## 📚 Электронная библиотека

### Сценарий
Создание цифровой библиотеки с функциями:
- Каталогизация книг и статей
- Семантический поиск по содержимому
- Рекомендации на основе интересов
- Академические исследования

### Пример реализации

#### 1. Система каталогизации библиотеки
```python
class DigitalLibrary:
    def __init__(self, api_base_url, librarian_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {librarian_token}"}
    
    def catalog_book(self, book_file_path, metadata):
        """Каталогизация книги с метаданными"""
        # Извлечение библиографической информации
        biblio_metadata = self._extract_bibliographic_data(metadata)
        
        # Определение тематических тегов
        subject_tags = self._determine_subject_tags(metadata)
        
        # Загрузка книги
        with open(book_file_path, 'rb') as file:
            files = {"file": file}
            data = {
                "title": metadata["title"],
                "tags": subject_tags,
                "metadata": biblio_metadata
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/documents",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()
    
    def _extract_bibliographic_data(self, metadata):
        """Извлечение библиографических данных"""
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "isbn": metadata.get("isbn", ""),
            "publisher": metadata.get("publisher", ""),
            "publication_year": metadata.get("year", ""),
            "pages": metadata.get("pages", 0),
            "language": metadata.get("language", "ru"),
            "subject": metadata.get("subject", []),
            "dewey_decimal": metadata.get("dewey", ""),
            "library_classification": metadata.get("classification", ""),
            "abstract": metadata.get("abstract", ""),
            "keywords": metadata.get("keywords", [])
        }
    
    def _determine_subject_tags(self, metadata):
        """Определение тематических тегов"""
        base_tags = ["библиотека", "книга"]
        
        # Тематические категории
        subject_mapping = {
            "история": ["история", "исторический"],
            "наука": ["наука", "научный", "исследование"],
            "техника": ["технический", "инженерия", "технология"],
            "литература": ["художественная", "поэзия", "проза"],
            "философия": ["философия", "этика", "логика"],
            "медицина": ["медицина", "здоровье", "лечение"],
            "экономика": ["экономика", "финансы", "бизнес"],
            "образование": ["образование", "педагогика", "обучение"]
        }
        
        subject = metadata.get("subject", [])
        keywords = metadata.get("keywords", [])
        
        for category, terms in subject_mapping.items():
            for term in terms:
                if any(term.lower() in s.lower() for s in subject + keywords):
                    base_tags.append(category)
                    break
        
        return base_tags
    
    def batch_catalog_books(self, books_directory):
        """Массовая каталогизация книг"""
        results = []
        
        # Поиск файлов метаданных
        for metadata_file in Path(books_directory).glob("*.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                # Поиск соответствующего файла книги
                book_file = self._find_book_file(metadata_file, metadata)
                
                if book_file and book_file.exists():
                    result = self.catalog_book(str(book_file), metadata)
                    results.append({
                        "book": metadata.get("title", book_file.name),
                        "status": "success",
                        "document_id": result.get("document", {}).get("id")
                    })
                else:
                    results.append({
                        "book": metadata.get("title", metadata_file.stem),
                        "status": "error",
                        "error": "Book file not found"
                    })
                    
            except Exception as e:
                results.append({
                    "book": metadata_file.stem,
                    "status": "error",
                    "error": str(e)
                })
        
        return results

# Пример метаданных книги
book_metadata = {
    "title": "Искусственный интеллект: современный подход",
    "author": "Стюарт Рассел, Питер Норвиг",
    "isbn": "978-5-8459-2006-9",
    "publisher": "Вильямс",
    "year": "2020",
    "pages": 1408,
    "language": "ru",
    "subject": ["Искусственный интеллект", "Машинное обучение", "Компьютерные науки"],
    "dewey": "006.3",
    "classification": "УДК 004.8",
    "abstract": "Фундаментальное руководство по искусственному интеллекту...",
    "keywords": ["ИИ", "алгоритмы", "нейронные сети", "машинное обучение"]
}

# Каталогизация
library = DigitalLibrary(
    api_base_url="https://api.rag-platform.com",
    librarian_token="LIBRARIAN_TOKEN"
)

result = library.catalog_book("ai_book.pdf", book_metadata)
```

#### 2. Академический поиск и исследования
```python
class AcademicResearch:
    def __init__(self, api_base_url, researcher_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {researcher_token}"}
    
    def literature_review(self, research_topic, max_sources=50):
        """Поиск литературы для обзора по теме исследования"""
        # Семантический поиск релевантных источников
        search_results = self._multi_query_search(research_topic)
        
        # Анализ и ранжирование источников
        ranked_sources = self._rank_academic_sources(search_results)
        
        # Генерация библиографии
        bibliography = self._generate_bibliography(ranked_sources[:max_sources])
        
        return {
            "research_topic": research_topic,
            "sources_found": len(ranked_sources),
            "selected_sources": ranked_sources[:max_sources],
            "bibliography": bibliography,
            "research_gaps": self._identify_research_gaps(ranked_sources)
        }
    
    def _multi_query_search(self, research_topic):
        """Многозапросный поиск для полного покрытия темы"""
        # Основные аспекты темы
        query_variations = [
            research_topic,
            f"{research_topic} методы исследования",
            f"{research_topic} современные подходы", 
            f"{research_topic} теоретические основы",
            f"{research_topic} практическое применение"
        ]
        
        all_results = []
        for query in query_variations:
            search_data = {
                "query": query,
                "limit": 30,
                "threshold": 0.6,
                "filters": {
                    "tags": ["наука", "исследование", "академический"],
                    "metadata.publication_year": {"gte": "2010"}  # Последние 10+ лет
                }
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/search/semantic",
                headers=self.headers,
                json=search_data
            )
            
            if response.status_code == 200:
                results = response.json()["results"]
                all_results.extend(results)
        
        # Удаление дубликатов
        unique_results = self._deduplicate_results(all_results)
        return unique_results
    
    def _rank_academic_sources(self, sources):
        """Ранжирование источников по академической значимости"""
        for source in sources:
            score = 0
            metadata = source.get("metadata", {})
            
            # Факторы ранжирования
            if metadata.get("publication_year"):
                year = int(metadata["publication_year"])
                if year >= 2020:
                    score += 10
                elif year >= 2015:
                    score += 5
            
            # Тип публикации
            if any(keyword in source["content"].lower() 
                   for keyword in ["журнал", "conference", "ieee", "acm"]):
                score += 15
            
            # Наличие ключевых терминов
            academic_terms = ["исследование", "анализ", "эксперимент", "методология"]
            term_count = sum(1 for term in academic_terms 
                           if term in source["content"].lower())
            score += term_count * 3
            
            # Релевантность (similarity score)
            score += source["score"] * 20
            
            source["academic_score"] = score
        
        return sorted(sources, key=lambda x: x["academic_score"], reverse=True)
    
    def generate_research_summary(self, research_topic, sources):
        """Генерация резюме исследования на основе источников"""
        # Подготовка контекста для RAG
        context_text = "\n\n".join([
            f"Источник: {s['metadata'].get('title', 'Неизвестный')}\n{s['content'][:1000]}"
            for s in sources[:10]
        ])
        
        rag_request = {
            "question": f"""На основе предоставленных академических источников создайте 
                          подробное резюме современного состояния исследований по теме '{research_topic}'.
                          Включите:
                          1. Основные направления исследований
                          2. Ключевые методы и подходы
                          3. Последние достижения
                          4. Открытые вопросы и проблемы
                          5. Перспективы развития""",
            "context_limit": 15,
            "include_sources": True,
            "model_params": {
                "temperature": 0.4,
                "max_tokens": 1500
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        
        return response.json() if response.status_code == 200 else None

# Пример академического исследования
researcher = AcademicResearch(
    api_base_url="https://api.rag-platform.com",
    researcher_token="RESEARCHER_TOKEN"
)

# Обзор литературы по машинному обучению
literature_review = researcher.literature_review(
    "глубокое обучение в обработке естественного языка"
)

print(f"Найдено источников: {literature_review['sources_found']}")
print(f"Отобрано для анализа: {len(literature_review['selected_sources'])}")

# Генерация резюме исследования
research_summary = researcher.generate_research_summary(
    "глубокое обучение в NLP",
    literature_review['selected_sources']
)

print("Резюме исследования:", research_summary["answer"])
```

## 🏥 Медицинская документация

### Сценарий
Система управления медицинской документацией для:
- Хранения медицинских протоколов и руководств
- Поиска симптомов и диагнозов
- Анализа клинических случаев
- Соблюдения медицинских стандартов

### Пример реализации

```python
class MedicalDocumentSystem:
    def __init__(self, api_base_url, medical_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {medical_token}"}
        
        # Медицинские специализации
        self.specializations = {
            "кардиология": ["сердце", "кардио", "аритмия", "инфаркт"],
            "неврология": ["нервная", "мозг", "невро", "инсульт"],
            "педиатрия": ["дети", "детская", "педиатр"],
            "онкология": ["рак", "опухоль", "онко", "новообразование"],
            "терапия": ["терапевт", "общая", "внутренние"],
            "хирургия": ["операция", "хирург", "оперативное"]
        }
    
    def upload_medical_protocol(self, protocol_file, protocol_metadata):
        """Загрузка медицинского протокола"""
        # Определение специализации
        specialization = self._determine_specialization(protocol_metadata)
        
        # Извлечение медицинских кодов
        medical_codes = self._extract_medical_codes(protocol_metadata)
        
        tags = [
            "медицинский", "протокол", specialization,
            protocol_metadata.get("protocol_type", "общий")
        ]
        
        metadata = {
            "specialization": specialization,
            "protocol_type": protocol_metadata.get("protocol_type"),
            "medical_codes": medical_codes,
            "approval_date": protocol_metadata.get("approval_date"),
            "version": protocol_metadata.get("version", "1.0"),
            "authority": protocol_metadata.get("authority", ""),
            "evidence_level": protocol_metadata.get("evidence_level", ""),
            "compliance_required": True
        }
        
        with open(protocol_file, 'rb') as file:
            files = {"file": file}
            data = {
                "title": protocol_metadata["title"],
                "tags": tags,
                "metadata": metadata
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/documents",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()
    
    def clinical_decision_support(self, symptoms, patient_data=None):
        """Система поддержки клинических решений"""
        # Поиск релевантных протоколов
        clinical_query = f"симптомы {symptoms} диагностика лечение"
        
        search_data = {
            "query": clinical_query,
            "limit": 15,
            "threshold": 0.7,
            "filters": {
                "tags": ["протокол", "диагностика", "лечение"],
                "metadata.compliance_required": True
            }
        }
        
        search_response = requests.post(
            f"{self.api_base_url}/api/v1/search/semantic",
            headers=self.headers,
            json=search_data
        )
        
        search_results = search_response.json()["results"]
        
        # Генерация клинических рекомендаций
        clinical_context = ""
        if patient_data:
            clinical_context = f"""
            Данные пациента:
            - Возраст: {patient_data.get('age', 'не указан')}
            - Пол: {patient_data.get('gender', 'не указан')}
            - Сопутствующие заболевания: {patient_data.get('comorbidities', 'отсутствуют')}
            - Принимаемые препараты: {patient_data.get('medications', 'отсутствуют')}
            """
        
        rag_request = {
            "question": f"""
            На основе медицинских протоколов проанализируйте следующие симптомы: {symptoms}
            
            {clinical_context}
            
            Предоставьте:
            1. Возможные диагнозы в порядке вероятности
            2. Рекомендуемые диагностические тесты
            3. Первоначальные терапевтические меры
            4. Критерии для направления к специалисту
            5. Признаки, требующие неотложной помощи
            
            ВАЖНО: Это только информационная поддержка. Окончательное решение принимает врач.
            """,
            "context_limit": 10,
            "include_sources": True,
            "filters": {
                "tags": ["протокол", "диагностика"],
                "metadata.compliance_required": True
            },
            "model_params": {
                "temperature": 0.2,  # Консервативные рекомендации
                "max_tokens": 1000
            }
        }
        
        rag_response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        
        clinical_recommendations = rag_response.json()
        
        return {
            "symptoms_analyzed": symptoms,
            "relevant_protocols": len(search_results),
            "clinical_recommendations": clinical_recommendations["answer"],
            "evidence_sources": clinical_recommendations["sources"],
            "confidence_level": clinical_recommendations["confidence_score"],
            "disclaimer": "Данная информация предназначена только для поддержки клинических решений. Окончательный диагноз и лечение определяет лечащий врач."
        }
    
    def drug_interaction_check(self, medications):
        """Проверка лекарственных взаимодействий"""
        drug_query = f"взаимодействие препаратов {' '.join(medications)}"
        
        search_data = {
            "query": drug_query,
            "limit": 10,
            "filters": {
                "tags": ["фармакология", "взаимодействие", "побочные"]
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/search/semantic",
            headers=self.headers,
            json=search_data
        )
        
        return response.json()

# Пример использования медицинской системы
medical_system = MedicalDocumentSystem(
    api_base_url="https://api.rag-platform.com",
    medical_token="MEDICAL_TOKEN"
)

# Клинический случай
patient_data = {
    "age": 45,
    "gender": "мужской",
    "comorbidities": ["гипертония", "диабет 2 типа"],
    "medications": ["метформин", "эналаприл"]
}

symptoms = "боль в груди, одышка, повышенное потоотделение"

# Получение клинических рекомендаций
clinical_support = medical_system.clinical_decision_support(
    symptoms=symptoms,
    patient_data=patient_data
)

print("Клинические рекомендации:")
print(clinical_support["clinical_recommendations"])
print(f"Уровень достоверности: {clinical_support['confidence_level']:.1%}")
```

## ⚖️ Правовые документы

### Сценарий
Система для юридических фирм и правовых отделов:
- База правовых актов и судебной практики
- Поиск прецедентов и аналогий
- Анализ договоров и соглашений
- Мониторинг изменений в законодательстве

### Пример реализации

```python
class LegalDocumentSystem:
    def __init__(self, api_base_url, legal_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {legal_token}"}
        
        # Типы правовых документов
        self.document_types = {
            "закон": ["федеральный закон", "кодекс", "конституция"],
            "подзаконный_акт": ["постановление", "приказ", "положение"],
            "судебная_практика": ["решение суда", "определение", "постановление суда"],
            "договор": ["соглашение", "контракт", "договор"],
            "правовая_позиция": ["разъяснение", "письмо", "позиция"]
        }
    
    def upload_legal_document(self, doc_file, legal_metadata):
        """Загрузка правового документа с правовой классификацией"""
        # Определение типа документа
        doc_type = self._classify_legal_document(legal_metadata)
        
        # Извлечение правовых реквизитов
        legal_attributes = self._extract_legal_attributes(legal_metadata)
        
        tags = [
            "правовой", doc_type,
            legal_metadata.get("legal_area", "общее право"),
            legal_metadata.get("jurisdiction", "РФ")
        ]
        
        metadata = {
            "document_type": doc_type,
            "legal_area": legal_metadata.get("legal_area"),
            "jurisdiction": legal_metadata.get("jurisdiction", "РФ"),
            "legal_force": legal_metadata.get("legal_force", "действующий"),
            "adoption_date": legal_metadata.get("adoption_date"),
            "effective_date": legal_metadata.get("effective_date"),
            "document_number": legal_metadata.get("document_number"),
            "issuing_authority": legal_metadata.get("issuing_authority"),
            "legal_hierarchy_level": legal_metadata.get("hierarchy_level"),
            "related_documents": legal_metadata.get("related_documents", []),
            "keywords": legal_metadata.get("keywords", [])
        }
        
        with open(doc_file, 'rb') as file:
            files = {"file": file}
            data = {
                "title": legal_metadata["title"],
                "tags": tags,
                "metadata": metadata
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/documents",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()
    
    def legal_research(self, legal_question, research_context=None):
        """Правовое исследование по заданному вопросу"""
        # Определение области права
        legal_area = self._determine_legal_area(legal_question)
        
        # Многоаспектный поиск
        search_queries = [
            legal_question,
            f"{legal_question} судебная практика",
            f"{legal_question} правовое регулирование",
            f"{legal_question} комментарий закона"
        ]
        
        all_results = []
        for query in search_queries:
            search_data = {
                "query": query,
                "limit": 20,
                "threshold": 0.6,
                "filters": {
                    "tags": ["правовой"],
                    "metadata.legal_area": legal_area,
                    "metadata.legal_force": "действующий"
                }
            }
            
            if research_context and "jurisdiction" in research_context:
                search_data["filters"]["metadata.jurisdiction"] = research_context["jurisdiction"]
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/search/semantic",
                headers=self.headers,
                json=search_data
            )
            
            if response.status_code == 200:
                results = response.json()["results"]
                all_results.extend(results)
        
        # Ранжирование по правовой значимости
        ranked_results = self._rank_legal_sources(all_results)
        
        # Генерация правового заключения
        legal_opinion = self._generate_legal_opinion(legal_question, ranked_results[:10])
        
        return {
            "legal_question": legal_question,
            "legal_area": legal_area,
            "sources_found": len(ranked_results),
            "primary_sources": [r for r in ranked_results if r.get("is_primary_source")],
            "judicial_practice": [r for r in ranked_results if "судебная_практика" in r.get("metadata", {}).get("document_type", "")],
            "legal_opinion": legal_opinion,
            "research_confidence": legal_opinion.get("confidence_score", 0)
        }
    
    def contract_analysis(self, contract_text, analysis_focus=None):
        """Анализ договора на предмет рисков и соответствия"""
        rag_request = {
            "question": f"""
            Проанализируйте предоставленный текст договора с точки зрения:
            
            1. Соответствия действующему законодательству РФ
            2. Потенциальных правовых рисков для сторон
            3. Недостающих или некорректных условий
            4. Рекомендаций по улучшению формулировок
            5. Ссылок на релевантные нормы права
            
            {f'Особое внимание уделите: {analysis_focus}' if analysis_focus else ''}
            
            Текст договора для анализа:
            {contract_text[:2000]}...
            """,
            "context_limit": 15,
            "include_sources": True,
            "filters": {
                "tags": ["договор", "гражданское право", "правовой"],
                "metadata.legal_force": "действующий"
            },
            "model_params": {
                "temperature": 0.3,
                "max_tokens": 1200
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        
        analysis_result = response.json()
        
        return {
            "contract_analysis": analysis_result["answer"],
            "legal_sources": analysis_result["sources"],
            "risk_level": self._assess_contract_risk(analysis_result),
            "recommendations": self._extract_recommendations(analysis_result["answer"])
        }
    
    def _rank_legal_sources(self, sources):
        """Ранжирование правовых источников по юридической силе"""
        hierarchy_weights = {
            "конституция": 100,
            "федеральный закон": 90,
            "кодекс": 85,
            "постановление правительства": 70,
            "приказ министерства": 60,
            "судебная практика ВС": 80,
            "судебная практика КС": 95,
            "судебная практика общей юрисдикции": 50
        }
        
        for source in sources:
            base_score = source["score"] * 10
            metadata = source.get("metadata", {})
            
            # Вес по иерархии источников права
            doc_type = metadata.get("document_type", "").lower()
            hierarchy_weight = 0
            for doc_pattern, weight in hierarchy_weights.items():
                if doc_pattern in doc_type:
                    hierarchy_weight = weight
                    break
            
            # Актуальность документа
            if metadata.get("legal_force") == "действующий":
                actuality_weight = 20
            elif metadata.get("legal_force") == "утратил силу":
                actuality_weight = -50
            else:
                actuality_weight = 0
            
            # Итоговый правовой рейтинг
            source["legal_score"] = base_score + hierarchy_weight + actuality_weight
            source["is_primary_source"] = hierarchy_weight >= 70
        
        return sorted(sources, key=lambda x: x["legal_score"], reverse=True)

# Пример правового исследования
legal_system = LegalDocumentSystem(
    api_base_url="https://api.rag-platform.com",
    legal_token="LEGAL_TOKEN"
)

# Правовое исследование
legal_question = "Права работника при увольнении по сокращению штатов"
research_context = {"jurisdiction": "РФ"}

legal_research = legal_system.legal_research(legal_question, research_context)

print(f"Область права: {legal_research['legal_area']}")
print(f"Найдено источников: {legal_research['sources_found']}")
print(f"Первичных источников: {len(legal_research['primary_sources'])}")
print(f"Судебной практики: {len(legal_research['judicial_practice'])}")
print("\nПравовое заключение:")
print(legal_research['legal_opinion']['answer'])
```

Продолжу с остальными примерами использования...

## 🔬 Научные исследования

### Сценарий
Платформа для научно-исследовательских институтов:
- Управление научными публикациями
- Анализ исследовательских данных
- Поиск коллабораций и грантов
- Отслеживание цитирований

### Пример реализации

```python
class ScientificResearchPlatform:
    def __init__(self, api_base_url, research_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {research_token}"}
        
        # Научные области
        self.research_fields = {
            "физика": ["квантовая", "ядерная", "теоретическая", "экспериментальная"],
            "химия": ["органическая", "неорганическая", "физическая", "аналитическая"],
            "биология": ["молекулярная", "клеточная", "генетика", "экология"],
            "математика": ["алгебра", "геометрия", "анализ", "статистика"],
            "информатика": ["алгоритмы", "машинное обучение", "базы данных", "сети"],
            "медицина": ["клиническая", "фармакология", "эпидемиология", "биомедицина"]
        }
    
    def submit_research_paper(self, paper_file, paper_metadata):
        """Подача научной статьи в репозиторий"""
        # Классификация по научной области
        research_field = self._classify_research_field(paper_metadata)
        
        # Извлечение научных метрик
        scientific_metrics = self._extract_scientific_metrics(paper_metadata)
        
        tags = [
            "научная статья", research_field,
            paper_metadata.get("publication_type", "журнальная статья"),
            paper_metadata.get("research_type", "экспериментальное")
        ]
        
        metadata = {
            "research_field": research_field,
            "authors": paper_metadata.get("authors", []),
            "affiliations": paper_metadata.get("affiliations", []),
            "publication_date": paper_metadata.get("publication_date"),
            "journal": paper_metadata.get("journal"),
            "doi": paper_metadata.get("doi"),
            "impact_factor": paper_metadata.get("impact_factor"),
            "keywords": paper_metadata.get("keywords", []),
            "abstract": paper_metadata.get("abstract"),
            "research_methods": paper_metadata.get("methods", []),
            "funding_sources": paper_metadata.get("funding", []),
            "ethical_approval": paper_metadata.get("ethical_approval"),
            "data_availability": paper_metadata.get("data_availability"),
            "supplementary_materials": paper_metadata.get("supplementary", [])
        }
        
        with open(paper_file, 'rb') as file:
            files = {"file": file}
            data = {
                "title": paper_metadata["title"],
                "tags": tags,
                "metadata": metadata
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/documents",
                headers=self.headers,
                files=files,
                data=data
            )
            return response.json()
    
    def research_collaboration_finder(self, research_interests, author_profile=None):
        """Поиск потенциальных коллабораций"""
        # Поиск исследователей с похожими интересами
        search_queries = [
            f"исследования {interest}" for interest in research_interests
        ]
        
        collaboration_candidates = []
        
        for query in search_queries:
            search_data = {
                "query": query,
                "limit": 15,
                "threshold": 0.7,
                "filters": {
                    "tags": ["научная статья"],
                    "metadata.publication_date": {"gte": "2020-01-01"}  # Последние 4 года
                }
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/search/semantic",
                headers=self.headers,
                json=search_data
            )
            
            if response.status_code == 200:
                results = response.json()["results"]
                for result in results:
                    authors = result.get("metadata", {}).get("authors", [])
                    affiliations = result.get("metadata", {}).get("affiliations", [])
                    
                    for author in authors:
                        if author_profile and author.lower() != author_profile.get("name", "").lower():
                            collaboration_candidates.append({
                                "author": author,
                                "affiliation": affiliations[0] if affiliations else "Unknown",
                                "research_area": result.get("metadata", {}).get("research_field"),
                                "recent_work": result.get("metadata", {}).get("title"),
                                "relevance_score": result["score"]
                            })
        
        # Агрегация и ранжирование кандидатов
        author_scores = {}
        for candidate in collaboration_candidates:
            author_key = f"{candidate['author']}_{candidate['affiliation']}"
            if author_key not in author_scores:
                author_scores[author_key] = {
                    "author": candidate["author"],
                    "affiliation": candidate["affiliation"],
                    "research_areas": set([candidate["research_area"]]),
                    "publications_count": 0,
                    "avg_relevance": 0,
                    "total_relevance": 0
                }
            
            author_scores[author_key]["publications_count"] += 1
            author_scores[author_key]["total_relevance"] += candidate["relevance_score"]
            author_scores[author_key]["research_areas"].add(candidate["research_area"])
        
        # Вычисление финального рейтинга
        for author_data in author_scores.values():
            author_data["avg_relevance"] = author_data["total_relevance"] / author_data["publications_count"]
            author_data["research_areas"] = list(author_data["research_areas"])
            author_data["collaboration_score"] = (
                author_data["avg_relevance"] * 10 +
                author_data["publications_count"] * 2 +
                len(author_data["research_areas"]) * 5
            )
        
        return sorted(author_scores.values(), 
                     key=lambda x: x["collaboration_score"], 
                     reverse=True)[:20]
    
    def grant_opportunity_analysis(self, research_proposal):
        """Анализ возможностей грантового финансирования"""
        rag_request = {
            "question": f"""
            На основе предложенного исследовательского проекта найдите и проанализируйте:
            
            1. Подходящие грантовые программы и фонды
            2. Требования к заявкам и критерии оценки
            3. Размеры типичного финансирования
            4. Успешные аналогичные проекты
            5. Рекомендации по подготовке заявки
            
            Описание исследовательского проекта:
            {research_proposal}
            """,
            "context_limit": 12,
            "include_sources": True,
            "filters": {
                "tags": ["грант", "финансирование", "научный фонд"],
            },
            "model_params": {
                "temperature": 0.4,
                "max_tokens": 1000
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        
        return response.json() if response.status_code == 200 else None
    
    def citation_impact_analysis(self, author_name, timeframe_years=5):
        """Анализ цитируемости и научного импакта"""
        # Поиск публикаций автора
        search_data = {
            "query": f"автор {author_name}",
            "limit": 50,
            "filters": {
                "tags": ["научная статья"],
                "metadata.authors": author_name,
                "metadata.publication_date": {
                    "gte": f"{datetime.now().year - timeframe_years}-01-01"
                }
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/search/semantic",
            headers=self.headers,
            json=search_data
        )
        
        if response.status_code != 200:
            return None
        
        publications = response.json()["results"]
        
        # Анализ публикаций
        impact_metrics = {
            "total_publications": len(publications),
            "research_fields": {},
            "collaboration_networks": set(),
            "journal_impact_factors": [],
            "publication_trends": {},
            "h_index_estimate": 0
        }
        
        for pub in publications:
            metadata = pub.get("metadata", {})
            
            # Области исследований
            field = metadata.get("research_field", "Unknown")
            impact_metrics["research_fields"][field] = impact_metrics["research_fields"].get(field, 0) + 1
            
            # Сети сотрудничества
            authors = metadata.get("authors", [])
            for author in authors:
                if author.lower() != author_name.lower():
                    impact_metrics["collaboration_networks"].add(author)
            
            # Импакт-факторы журналов
            if metadata.get("impact_factor"):
                impact_metrics["journal_impact_factors"].append(float(metadata["impact_factor"]))
            
            # Тренды публикаций по годам
            pub_date = metadata.get("publication_date", "")
            if pub_date:
                year = pub_date[:4]
                impact_metrics["publication_trends"][year] = impact_metrics["publication_trends"].get(year, 0) + 1
        
        # Вычисление метрик
        impact_metrics["collaboration_networks"] = list(impact_metrics["collaboration_networks"])
        impact_metrics["avg_impact_factor"] = (
            sum(impact_metrics["journal_impact_factors"]) / len(impact_metrics["journal_impact_factors"])
            if impact_metrics["journal_impact_factors"] else 0
        )
        
        return impact_metrics

# Пример использования научной платформы
research_platform = ScientificResearchPlatform(
    api_base_url="https://api.rag-platform.com",
    research_token="RESEARCH_TOKEN"
)

# Поиск коллабораций
research_interests = ["машинное обучение", "нейронные сети", "обработка естественного языка"]
author_profile = {"name": "И.И. Иванов", "affiliation": "МГУ"}

collaborations = research_platform.research_collaboration_finder(
    research_interests=research_interests,
    author_profile=author_profile
)

print("Топ-5 кандидатов для коллаборации:")
for i, candidate in enumerate(collaborations[:5], 1):
    print(f"{i}. {candidate['author']} ({candidate['affiliation']})")
    print(f"   Области: {', '.join(candidate['research_areas'])}")
    print(f"   Рейтинг: {candidate['collaboration_score']:.1f}")
    print()
```

Создаю остальную документацию:

## 📊 Бизнес-аналитика

### Сценарий
Система для аналитических отделов компаний:
- Анализ бизнес-отчетов и финансовых данных
- Мониторинг рыночных трендов
- Конкурентная разведка
- Прогнозирование и планирование

### Пример реализации

```python
class BusinessAnalyticsPlatform:
    def __init__(self, api_base_url, analyst_token):
        self.api_base_url = api_base_url
        self.headers = {"Authorization": f"Bearer {analyst_token}"}
    
    def market_trend_analysis(self, industry, time_period="2023-2024"):
        """Анализ рыночных трендов по отрасли"""
        trend_queries = [
            f"{industry} рыночные тенденции {time_period}",
            f"{industry} прогноз развития",
            f"{industry} конкуренция анализ",
            f"{industry} потребительское поведение"
        ]
        
        trend_data = []
        for query in trend_queries:
            search_data = {
                "query": query,
                "limit": 15,
                "threshold": 0.6,
                "filters": {
                    "tags": ["аналитика", "отчет", "исследование"],
                    "metadata.report_type": "market_analysis"
                }
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/v1/search/semantic",
                headers=self.headers,
                json=search_data
            )
            
            if response.status_code == 200:
                trend_data.extend(response.json()["results"])
        
        # Генерация аналитического отчета
        rag_request = {
            "question": f"""
            На основе собранных данных подготовьте аналитический отчет о рыночных тенденциях в отрасли {industry}:
            
            1. Ключевые тренды и драйверы роста
            2. Размер рынка и прогнозы
            3. Конкурентная среда
            4. Потребительские предпочтения
            5. Риски и возможности
            6. Рекомендации для бизнеса
            """,
            "context_limit": 20,
            "include_sources": True,
            "model_params": {
                "temperature": 0.4,
                "max_tokens": 1500
            }
        }
        
        response = requests.post(
            f"{self.api_base_url}/api/v1/answers/rag",
            headers=self.headers,
            json=rag_request
        )
        
        return response.json() if response.status_code == 200 else None

# Использование
analytics = BusinessAnalyticsPlatform(
    api_base_url="https://api.rag-platform.com",
    analyst_token="ANALYST_TOKEN"
)

market_report = analytics.market_trend_analysis("электронная коммерция")
print("Анализ рынка:", market_report["answer"])
```

Создаю скрипты для видео-туториалов:

<function_calls>
<invoke name="todo_write">
<parameter name="merge">true
