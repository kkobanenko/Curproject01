from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import email
from email import policy
from email.parser import BytesParser

from .document_parser import DocumentParser

logger = logging.getLogger(__name__)

class EMLParser(DocumentParser):
    """Парсер для EML файлов с поддержкой метаданных и вложений"""
    
    def __init__(self):
        super().__init__()
        self.supported_mime_types = ['message/rfc822']
    
    def can_parse(self, file_path: Path) -> bool:
        """Проверяет, может ли парсер обработать EML файл"""
        return (file_path.suffix.lower() == '.eml' and 
                file_path.exists())
    
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Парсит EML документ"""
        if not self.can_parse(file_path):
            raise ValueError(f"Cannot parse file: {file_path}")
        
        # Вычисляем SHA256
        sha256 = self._calculate_sha256(file_path)
        
        # Определяем MIME тип
        mime_type = self.get_mime_type(file_path)
        
        # Парсим содержимое
        content = self._extract_content(file_path)
        
        return {
            'title': content.get('title'),
            'text': content.get('text', ''),
            'tables': content.get('tables', []),
            'pages': content.get('pages', []),
            'sha256': sha256,
            'mime_type': mime_type,
            'needs_ocr': False,  # EML не нужен OCR
            'metadata': content.get('metadata', {}),
            'attachments_count': content.get('attachments_count', 0),
            'has_attachments': content.get('attachments_count', 0) > 0,
            'email_type': 'eml'
        }
    
    def _extract_content(self, file_path: Path) -> Dict[str, Any]:
        """Извлекает содержимое EML"""
        content = {
            'text': '',
            'tables': [],
            'pages': [],
            'metadata': {},
            'attachments_count': 0
        }
        
        try:
            with open(file_path, 'rb') as file:
                eml_content = file.read()
            
            # Парсим email
            msg = BytesParser(policy=policy.default).parsebytes(eml_content)
            
            # Метаданные
            content['metadata'] = self._extract_metadata(msg)
            content['title'] = content['metadata'].get('subject')
            
            # Текст
            content['text'] = self._extract_text(msg)
            
            # Вложения
            attachments = self._extract_attachments(msg)
            content['attachments_count'] = len(attachments)
            
            # Создаем "страницы" для совместимости
            content['pages'] = [{'page_num': 1, 'text': content['text'][:1000] + '...'}]
            
        except Exception as e:
            logger.error(f"Error parsing EML {file_path}: {e}")
            raise
        
        return content
    
    def _extract_metadata(self, msg) -> Dict[str, Any]:
        """Извлекает метаданные из email"""
        metadata = {}
        
        # Основные заголовки
        headers = [
            'Subject', 'From', 'To', 'Cc', 'Bcc', 'Date', 'Message-ID',
            'In-Reply-To', 'References', 'Reply-To', 'Sender', 'Return-Path',
            'X-Mailer', 'X-Priority', 'X-MSMail-Priority', 'Importance',
            'MIME-Version', 'Content-Type', 'Content-Transfer-Encoding'
        ]
        
        for header in headers:
            value = msg.get(header)
            if value:
                metadata[header.lower()] = str(value)
        
        # Дополнительные заголовки
        for header, value in msg.items():
            if header not in headers:
                metadata[f"header_{header.lower()}"] = str(value)
        
        # Парсим адреса
        if 'from' in metadata:
            metadata['from_parsed'] = self._parse_email_address(metadata['from'])
        
        if 'to' in metadata:
            metadata['to_parsed'] = self._parse_email_address(metadata['to'])
        
        if 'cc' in metadata:
            metadata['cc_parsed'] = self._parse_email_address(metadata['cc'])
        
        return metadata
    
    def _parse_email_address(self, address_string: str) -> Dict[str, Any]:
        """Парсит email адрес"""
        try:
            from email.utils import parseaddr
            name, email_addr = parseaddr(address_string)
            return {
                'name': name,
                'email': email_addr,
                'original': address_string
            }
        except Exception:
            return {
                'name': '',
                'email': address_string,
                'original': address_string
            }
    
    def _extract_text(self, msg) -> str:
        """Извлекает текст из email"""
        text_parts = []
        
        if msg.is_multipart():
            # Мультипартное сообщение
            for part in msg.walk():
                content_type = part.get_content_type()
                
                if content_type == "text/plain":
                    try:
                        text = part.get_content()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from part: {e}")
                
                elif content_type == "text/html":
                    try:
                        # Конвертируем HTML в текст
                        html_text = part.get_content()
                        if html_text:
                            # Простое удаление HTML тегов
                            import re
                            clean_text = re.sub(r'<[^>]+>', '', html_text)
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            if clean_text:
                                text_parts.append(clean_text)
                    except Exception as e:
                        logger.warning(f"Error extracting HTML text: {e}")
        else:
            # Простое сообщение
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                try:
                    text = msg.get_content()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Error extracting text: {e}")
            elif content_type == "text/html":
                try:
                    html_text = msg.get_content()
                    if html_text:
                        import re
                        clean_text = re.sub(r'<[^>]+>', '', html_text)
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                        if clean_text:
                            text_parts.append(clean_text)
                except Exception as e:
                    logger.warning(f"Error extracting HTML text: {e}")
        
        return '\n\n'.join(text_parts)
    
    def _extract_attachments(self, msg) -> List[Dict[str, Any]]:
        """Извлекает информацию о вложениях"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_filename():
                    attachment_info = {
                        'filename': part.get_filename(),
                        'content_type': part.get_content_type(),
                        'size': len(part.get_payload(decode=True)) if part.get_payload() else 0,
                        'content_disposition': part.get('Content-Disposition', ''),
                        'content_id': part.get('Content-ID', '')
                    }
                    attachments.append(attachment_info)
        
        return attachments
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
