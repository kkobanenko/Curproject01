"""
Сервис экспорта данных в различные форматы
"""
import csv
import json
import xml.etree.ElementTree as ET
import io
import zipfile
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging
import pandas as pd
from pathlib import Path

from ..schemas.webhooks import DataExportRequest, DataExportJob
from ..schemas.auth import UserContext
from ..services.audit import AuditService, AuditAction, AuditLevel

logger = logging.getLogger(__name__)


class DataExportService:
    """Сервис для экспорта данных в различные форматы"""
    
    def __init__(self, export_dir: str = "/tmp/exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        
        # Поддерживаемые форматы
        self.supported_formats = {
            "json": self._export_json,
            "csv": self._export_csv, 
            "xml": self._export_xml,
            "excel": self._export_excel,
            "yaml": self._export_yaml
        }
    
    async def create_export(
        self,
        export_request: DataExportRequest,
        user_context: UserContext
    ) -> DataExportJob:
        """Создание задачи экспорта"""
        
        # Генерируем ID задачи
        job_id = f"export_{user_context.user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Создаем задачу
        export_job = DataExportJob(
            id=job_id,
            request=export_request,
            status="created",
            created_by=user_context.user_id
        )
        
        # Логируем создание задачи
        AuditService.log_action(
            action=AuditAction.EXPORT_DATA,
            level=AuditLevel.INFO,
            user_context=user_context,
            resource_type="export_job",
            resource_id=job_id,
            details={
                "export_type": export_request.export_type,
                "format": export_request.format,
                "include_content": export_request.include_content,
                "max_records": export_request.max_records
            }
        )
        
        return export_job
    
    async def process_export(
        self,
        export_job: DataExportJob,
        user_context: UserContext
    ) -> DataExportJob:
        """Обработка задачи экспорта"""
        
        try:
            export_job.status = "processing"
            export_job.started_at = datetime.utcnow()
            
            # Получаем данные
            data = await self._get_export_data(export_job.request, user_context)
            export_job.total_records = len(data)
            
            # Проверяем лимиты
            if len(data) > export_job.request.max_records:
                data = data[:export_job.request.max_records]
                logger.warning(f"Данные обрезаны до {export_job.request.max_records} записей")
            
            # Экспортируем данные
            file_path = await self._export_data(
                data=data,
                format_type=export_job.request.format,
                job_id=export_job.id,
                compress=export_job.request.compress
            )
            
            # Обновляем статус
            export_job.status = "completed"
            export_job.completed_at = datetime.utcnow()
            export_job.progress_percent = 100.0
            export_job.records_processed = len(data)
            export_job.file_size_bytes = file_path.stat().st_size
            export_job.download_url = f"/api/v1/export/{export_job.id}/download"
            export_job.expires_at = datetime.utcnow() + timedelta(hours=24)  # Файл доступен 24 часа
            
            logger.info(f"Экспорт {export_job.id} завершен. Обработано {len(data)} записей")
            
        except Exception as e:
            export_job.status = "failed"
            export_job.error_message = str(e)
            logger.error(f"Ошибка обработки экспорта {export_job.id}: {e}")
            
            # Логируем ошибку
            AuditService.log_action(
                action=AuditAction.EXPORT_DATA,
                level=AuditLevel.WARNING,
                user_context=user_context,
                resource_type="export_job",
                resource_id=export_job.id,
                success=False,
                error_message=str(e)
            )
        
        return export_job
    
    async def _get_export_data(
        self,
        request: DataExportRequest,
        user_context: UserContext
    ) -> List[Dict[str, Any]]:
        """Получение данных для экспорта"""
        
        # TODO: Реализовать получение данных из базы данных
        # Пока возвращаем тестовые данные
        
        if request.export_type == "documents":
            return await self._get_documents_data(request, user_context)
        elif request.export_type == "users":
            return await self._get_users_data(request, user_context)
        elif request.export_type == "search_queries":
            return await self._get_search_queries_data(request, user_context)
        elif request.export_type == "audit_logs":
            return await self._get_audit_logs_data(request, user_context)
        else:
            raise ValueError(f"Неподдерживаемый тип экспорта: {request.export_type}")
    
    async def _get_documents_data(
        self,
        request: DataExportRequest,
        user_context: UserContext
    ) -> List[Dict[str, Any]]:
        """Получение данных документов"""
        
        # Тестовые данные документов
        documents = [
            {
                "id": f"doc_{i}",
                "title": f"Документ {i}",
                "filename": f"document_{i}.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024 * (i + 1),
                "created_at": datetime.utcnow().isoformat(),
                "tenant_id": user_context.tenant_id,
                "uploaded_by": user_context.username,
                "content": f"Содержимое документа {i}" if request.include_content else None,
                "metadata": {
                    "author": f"Автор {i}",
                    "tags": [f"tag{i}", f"category{i % 3}"],
                    "version": "1.0"
                } if request.include_metadata else None
            }
            for i in range(1, min(request.max_records + 1, 101))  # Максимум 100 тестовых записей
        ]
        
        # Применяем фильтры
        filtered_documents = []
        for doc in documents:
            # Фильтр по датам
            doc_date = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
            if request.date_from and doc_date < request.date_from:
                continue
            if request.date_to and doc_date > request.date_to:
                continue
            
            # Фильтр по тенанту
            if request.tenant_id and doc["tenant_id"] != request.tenant_id:
                continue
            
            # Фильтр по типу документа
            if request.document_types and doc["content_type"] not in request.document_types:
                continue
            
            filtered_documents.append(doc)
        
        return filtered_documents
    
    async def _get_users_data(
        self,
        request: DataExportRequest,
        user_context: UserContext
    ) -> List[Dict[str, Any]]:
        """Получение данных пользователей"""
        
        # Тестовые данные пользователей
        users = [
            {
                "id": i,
                "username": f"user_{i}",
                "email": f"user{i}@example.com",
                "tenant_id": user_context.tenant_id,
                "role": "user" if i % 3 != 0 else "admin",
                "created_at": datetime.utcnow().isoformat(),
                "last_login": datetime.utcnow().isoformat(),
                "is_active": i % 5 != 0,  # 80% активных пользователей
                "metadata": {
                    "department": f"Отдел {i % 5}",
                    "position": f"Должность {i % 3}"
                } if request.include_metadata else None
            }
            for i in range(1, min(request.max_records + 1, 51))  # Максимум 50 пользователей
        ]
        
        return users
    
    async def _get_search_queries_data(
        self,
        request: DataExportRequest,
        user_context: UserContext
    ) -> List[Dict[str, Any]]:
        """Получение данных поисковых запросов"""
        
        queries = [
            {
                "id": f"query_{i}",
                "query_text": f"поисковый запрос {i}",
                "user_id": user_context.user_id,
                "tenant_id": user_context.tenant_id,
                "results_count": i * 3,
                "response_time_ms": 150 + (i * 10),
                "created_at": datetime.utcnow().isoformat(),
                "query_type": "semantic" if i % 2 == 0 else "keyword"
            }
            for i in range(1, min(request.max_records + 1, 201))  # Максимум 200 запросов
        ]
        
        return queries
    
    async def _get_audit_logs_data(
        self,
        request: DataExportRequest,
        user_context: UserContext
    ) -> List[Dict[str, Any]]:
        """Получение данных аудит логов"""
        
        logs = [
            {
                "id": i,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_context.user_id,
                "action": ["login", "document_view", "search", "logout"][i % 4],
                "resource_type": "document" if i % 2 == 0 else "user",
                "resource_id": f"resource_{i}",
                "success": i % 10 != 0,  # 90% успешных операций
                "ip_address": f"192.168.1.{i % 255}",
                "user_agent": "Mozilla/5.0 (compatible)",
                "details": {
                    "additional_info": f"Дополнительная информация {i}"
                } if request.include_metadata else None
            }
            for i in range(1, min(request.max_records + 1, 501))  # Максимум 500 логов
        ]
        
        return logs
    
    async def _export_data(
        self,
        data: List[Dict[str, Any]],
        format_type: str,
        job_id: str,
        compress: bool = False
    ) -> Path:
        """Экспорт данных в указанный формат"""
        
        if format_type not in self.supported_formats:
            raise ValueError(f"Неподдерживаемый формат: {format_type}")
        
        # Экспортируем данные
        export_func = self.supported_formats[format_type]
        file_path = await export_func(data, job_id)
        
        # Сжимаем если нужно
        if compress:
            file_path = await self._compress_file(file_path)
        
        return file_path
    
    async def _export_json(self, data: List[Dict[str, Any]], job_id: str) -> Path:
        """Экспорт в JSON формат"""
        file_path = self.export_dir / f"{job_id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        return file_path
    
    async def _export_csv(self, data: List[Dict[str, Any]], job_id: str) -> Path:
        """Экспорт в CSV формат"""
        file_path = self.export_dir / f"{job_id}.csv"
        
        if not data:
            # Создаем пустой файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")
            return file_path
        
        # Получаем все возможные ключи
        all_keys = set()
        for item in data:
            all_keys.update(self._flatten_dict(item).keys())
        
        fieldnames = sorted(all_keys)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                flattened = self._flatten_dict(item)
                # Дополняем отсутствующие ключи пустыми значениями
                row = {key: flattened.get(key, '') for key in fieldnames}
                writer.writerow(row)
        
        return file_path
    
    async def _export_xml(self, data: List[Dict[str, Any]], job_id: str) -> Path:
        """Экспорт в XML формат"""
        file_path = self.export_dir / f"{job_id}.xml"
        
        # Создаем корневой элемент
        root = ET.Element("export")
        root.set("generated_at", datetime.utcnow().isoformat())
        root.set("records_count", str(len(data)))
        
        # Добавляем данные
        for item in data:
            record = ET.SubElement(root, "record")
            self._dict_to_xml(item, record)
        
        # Записываем в файл
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
        return file_path
    
    async def _export_excel(self, data: List[Dict[str, Any]], job_id: str) -> Path:
        """Экспорт в Excel формат"""
        file_path = self.export_dir / f"{job_id}.xlsx"
        
        if not data:
            # Создаем пустой DataFrame
            df = pd.DataFrame()
        else:
            # Преобразуем данные в плоский формат
            flattened_data = [self._flatten_dict(item) for item in data]
            df = pd.DataFrame(flattened_data)
        
        # Записываем в Excel
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Export')
            
            # Добавляем лист с метаданными
            metadata_df = pd.DataFrame([
                ["Generated at", datetime.utcnow().isoformat()],
                ["Records count", len(data)],
                ["Export job ID", job_id]
            ], columns=["Parameter", "Value"])
            
            metadata_df.to_excel(writer, index=False, sheet_name='Metadata')
        
        return file_path
    
    async def _export_yaml(self, data: List[Dict[str, Any]], job_id: str) -> Path:
        """Экспорт в YAML формат"""
        file_path = self.export_dir / f"{job_id}.yaml"
        
        try:
            import yaml
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            # Если PyYAML не установлен, экспортируем как JSON
            logger.warning("PyYAML не установлен, экспортируем как JSON")
            return await self._export_json(data, job_id)
        
        return file_path
    
    async def _compress_file(self, file_path: Path) -> Path:
        """Сжатие файла в ZIP архив"""
        zip_path = file_path.with_suffix(file_path.suffix + '.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, file_path.name)
        
        # Удаляем оригинальный файл
        file_path.unlink()
        
        return zip_path
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Преобразование вложенного словаря в плоский"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Преобразуем список в строку
                items.append((new_key, json.dumps(v, ensure_ascii=False, default=str)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element):
        """Преобразование словаря в XML элементы"""
        for key, value in data.items():
            # Очищаем ключ от недопустимых символов
            clean_key = ''.join(c for c in str(key) if c.isalnum() or c in ['_', '-'])
            if not clean_key:
                clean_key = "item"
            
            if isinstance(value, dict):
                child = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, child)
            elif isinstance(value, list):
                child = ET.SubElement(parent, clean_key)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_elem = ET.SubElement(child, f"item_{i}")
                        self._dict_to_xml(item, item_elem)
                    else:
                        item_elem = ET.SubElement(child, f"item_{i}")
                        item_elem.text = str(item)
            else:
                child = ET.SubElement(parent, clean_key)
                child.text = str(value) if value is not None else ""
    
    def get_file_path(self, job_id: str) -> Optional[Path]:
        """Получение пути к файлу экспорта"""
        # Ищем файл с любым расширением
        for ext in ['.json', '.csv', '.xml', '.xlsx', '.yaml', '.zip']:
            file_path = self.export_dir / f"{job_id}{ext}"
            if file_path.exists():
                return file_path
        return None
    
    def cleanup_expired_exports(self, max_age_hours: int = 24):
        """Очистка просроченных файлов экспорта"""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        cleaned_count = 0
        for file_path in self.export_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Ошибка удаления файла {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Очищено {cleaned_count} просроченных файлов экспорта")


# Глобальный экземпляр сервиса
data_export_service = DataExportService()
