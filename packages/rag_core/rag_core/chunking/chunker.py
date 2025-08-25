from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """Чанк документа"""
    text: str
    chunk_index: int
    chunk_type: str  # 'text', 'table', 'mixed'
    page_no: Optional[int] = None
    table_html: Optional[str] = None
    bbox: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    source_doc_id: Optional[str] = None

class ChunkingStrategy:
    """Базовая стратегия чанкинга"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def create_chunks(self, content: Dict[str, Any]) -> List[Chunk]:
        """Создает чанки из содержимого документа"""
        raise NotImplementedError

class TextChunkingStrategy(ChunkingStrategy):
    """Стратегия чанкинга текста"""
    
    def create_chunks(self, content: Dict[str, Any]) -> List[Chunk]:
        """Создает текстовые чанки"""
        text = content.get('text', '')
        if not text.strip():
            return []
        
        chunks = []
        chunk_index = 0
        
        # Разбиваем на предложения для лучшего качества
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Если добавление предложения превысит размер чанка
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Создаем чанк
                chunk_text = ' '.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    chunk_type='text',
                    metadata={
                        'chunk_size': current_length,
                        'sentence_count': len(current_chunk),
                        'strategy': 'sentence_based'
                    }
                ))
                
                # Начинаем новый чанк с overlap
                if self.overlap > 0:
                    overlap_sentences = self._get_overlap_sentences(current_chunk, self.overlap)
                    current_chunk = overlap_sentences
                    current_length = sum(len(s) + 1 for s in overlap_sentences)
                else:
                    current_chunk = []
                    current_length = 0
                
                chunk_index += 1
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Добавляем последний чанк
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=chunk_index,
                chunk_type='text',
                metadata={
                    'chunk_size': current_length,
                    'sentence_count': len(current_chunk),
                    'strategy': 'sentence_based'
                }
            ))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения"""
        # Простое разбиение по знакам препинания
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def _get_overlap_sentences(self, sentences: List[str], target_length: int) -> List[str]:
        """Получает предложения для overlap"""
        overlap_sentences = []
        current_length = 0
        
        for sentence in reversed(sentences):
            if current_length + len(sentence) <= target_length:
                overlap_sentences.insert(0, sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        return overlap_sentences

class TableChunkingStrategy(ChunkingStrategy):
    """Стратегия чанкинга таблиц"""
    
    def create_chunks(self, content: Dict[str, Any]) -> List[Chunk]:
        """Создает чанки из таблиц"""
        tables = content.get('tables', [])
        if not tables:
            return []
        
        chunks = []
        chunk_index = 0
        
        for table in tables:
            # Каждая таблица становится отдельным чанком
            table_text = self._table_to_text(table)
            table_html = self._table_to_html(table)
            
            chunks.append(Chunk(
                text=table_text,
                chunk_index=chunk_index,
                chunk_type='table',
                page_no=table.get('page', 1),
                table_html=table_html,
                metadata={
                    'table_index': table.get('table_index', 0),
                    'rows': table.get('rows', 0),
                    'cols': table.get('cols', 0),
                    'extraction_method': table.get('extraction_method', 'unknown'),
                    'accuracy': table.get('accuracy', 0),
                    'strategy': 'table_based'
                }
            ))
            chunk_index += 1
        
        return chunks
    
    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """Конвертирует таблицу в текстовое представление"""
        data = table.get('data', [])
        if not data:
            return "Empty table"
        
        text_lines = []
        
        # Добавляем заголовки если есть
        if data:
            text_lines.append(" | ".join(str(cell) for cell in data[0]))
            text_lines.append("-" * len(text_lines[0]))
            
            # Добавляем данные
            for row in data[1:]:
                text_lines.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(text_lines)
    
    def _table_to_html(self, table: Dict[str, Any]) -> str:
        """Конвертирует таблицу в HTML"""
        data = table.get('data', [])
        if not data:
            return "<table><tr><td>Empty table</td></tr></table>"
        
        html_parts = ["<table border='1'>"]
        
        for i, row in enumerate(data):
            tag = "th" if i == 0 else "td"
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(f"<{tag}>{cell}</{tag}>")
            html_parts.append("</tr>")
        
        html_parts.append("</table>")
        return "".join(html_parts)

class MixedChunkingStrategy(ChunkingStrategy):
    """Стратегия смешанного чанкинга (текст + таблицы)"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        super().__init__(chunk_size, overlap)
        self.text_strategy = TextChunkingStrategy(chunk_size, overlap)
        self.table_strategy = TableChunkingStrategy(chunk_size, overlap)
    
    def create_chunks(self, content: Dict[str, Any]) -> List[Chunk]:
        """Создает смешанные чанки"""
        chunks = []
        
        # Создаем чанки из таблиц
        table_chunks = self.table_strategy.create_chunks(content)
        chunks.extend(table_chunks)
        
        # Создаем чанки из текста
        text_chunks = self.text_strategy.create_chunks(content)
        
        # Обновляем индексы текстовых чанков
        for i, chunk in enumerate(text_chunks):
            chunk.chunk_index = len(chunks) + i
        
        chunks.extend(text_chunks)
        
        # Сортируем по индексу
        chunks.sort(key=lambda x: x.chunk_index)
        
        return chunks

class DocumentChunker:
    """Основной класс для чанкинга документов"""
    
    def __init__(self, strategy: str = 'mixed', chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = self._get_strategy(strategy, chunk_size, overlap)
    
    def _get_strategy(self, strategy: str, chunk_size: int, overlap: int) -> ChunkingStrategy:
        """Возвращает стратегию чанкинга"""
        strategies = {
            'text': TextChunkingStrategy,
            'table': TableChunkingStrategy,
            'mixed': MixedChunkingStrategy
        }
        
        strategy_class = strategies.get(strategy, MixedChunkingStrategy)
        return strategy_class(chunk_size, overlap)
    
    def chunk_document(self, content: Dict[str, Any]) -> List[Chunk]:
        """Разбивает документ на чанки"""
        try:
            chunks = self.strategy.create_chunks(content)
            logger.info(f"Created {len(chunks)} chunks using {self.strategy.__class__.__name__}")
            return chunks
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            raise
    
    def get_chunk_statistics(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Возвращает статистику по чанкам"""
        if not chunks:
            return {}
        
        text_chunks = [c for c in chunks if c.chunk_type == 'text']
        table_chunks = [c for c in chunks if c.chunk_type == 'table']
        
        total_text_length = sum(len(c.text) for c in text_chunks)
        total_table_length = sum(len(c.text) for c in table_chunks)
        
        return {
            'total_chunks': len(chunks),
            'text_chunks': len(text_chunks),
            'table_chunks': len(table_chunks),
            'total_text_length': total_text_length,
            'total_table_length': total_table_length,
            'average_chunk_size': (total_text_length + total_table_length) / len(chunks) if chunks else 0,
            'chunk_types': {
                'text': len(text_chunks),
                'table': len(table_chunks)
            }
        }
