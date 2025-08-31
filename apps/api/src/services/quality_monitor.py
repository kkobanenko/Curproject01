"""
Сервис для мониторинга качества поиска и ответов
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import clickhouse_connect
from ..settings.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SearchQualityMetrics:
    """Метрики качества поиска"""
    query_id: str
    query_text: str
    relevance_score: float
    precision_score: float
    recall_score: float
    f1_score: float
    user_feedback: Optional[str] = None
    response_quality: float = 0.0


@dataclass
class ResponseQualityMetrics:
    """Метрики качества ответов"""
    response_id: str
    response_text: str
    coherence_score: float
    relevance_score: float
    completeness_score: float
    accuracy_score: float
    user_rating: Optional[int] = None
    response_time_ms: int = 0


class QualityMonitor:
    """Монитор качества поиска и ответов"""
    
    def __init__(self):
        self.clickhouse_client = None
        self._initialize_clickhouse()
        self.quality_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 50
        
    def _initialize_clickhouse(self):
        """Инициализация подключения к ClickHouse"""
        try:
            self.clickhouse_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD,
                database=settings.CLICKHOUSE_DATABASE
            )
            logger.info("ClickHouse connection initialized for quality monitoring")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse for quality monitoring: {e}")
            self.clickhouse_client = None
    
    def calculate_relevance_score(self, query: str, results: List[Dict[str, Any]]) -> float:
        """Расчет релевантности результатов поиска"""
        if not results:
            return 0.0
        
        try:
            # Простая эвристика на основе длины совпадений
            query_words = set(query.lower().split())
            total_score = 0.0
            
            for result in results:
                content = result.get('content', '').lower()
                content_words = set(content.split())
                
                # Подсчет пересечений слов
                intersection = len(query_words.intersection(content_words))
                union = len(query_words.union(content_words))
                
                if union > 0:
                    jaccard_similarity = intersection / union
                    total_score += jaccard_similarity
            
            return min(total_score / len(results), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    def calculate_precision_score(self, query: str, results: List[Dict[str, Any]], 
                                relevant_threshold: float = 0.5) -> float:
        """Расчет точности поиска"""
        if not results:
            return 0.0
        
        try:
            relevant_count = 0
            
            for result in results:
                # Простая эвристика релевантности
                content = result.get('content', '').lower()
                query_words = set(query.lower().split())
                content_words = set(content.split())
                
                intersection = len(query_words.intersection(content_words))
                if intersection / len(query_words) >= relevant_threshold:
                    relevant_count += 1
            
            return relevant_count / len(results)
            
        except Exception as e:
            logger.error(f"Error calculating precision score: {e}")
            return 0.0
    
    def calculate_recall_score(self, query: str, results: List[Dict[str, Any]], 
                             total_relevant_docs: int) -> float:
        """Расчет полноты поиска"""
        if total_relevant_docs == 0:
            return 1.0 if not results else 0.0
        
        try:
            relevant_found = 0
            
            for result in results:
                content = result.get('content', '').lower()
                query_words = set(query.lower().split())
                content_words = set(content.split())
                
                intersection = len(query_words.intersection(content_words))
                if intersection / len(query_words) >= 0.5:  # Порог релевантности
                    relevant_found += 1
            
            return min(relevant_found / total_relevant_docs, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating recall score: {e}")
            return 0.0
    
    def calculate_f1_score(self, precision: float, recall: float) -> float:
        """Расчет F1-меры"""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def analyze_response_quality(self, response_text: str) -> Dict[str, float]:
        """Анализ качества ответа"""
        try:
            # Простые метрики качества ответа
            metrics = {
                'coherence_score': 0.0,
                'relevance_score': 0.0,
                'completeness_score': 0.0,
                'accuracy_score': 0.0
            }
            
            if not response_text:
                return metrics
            
            # Анализ связности (длина предложений, структура)
            sentences = response_text.split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            
            # Нормализация длины предложений (оптимальная длина 15-20 слов)
            if 10 <= avg_sentence_length <= 25:
                metrics['coherence_score'] = 1.0
            elif 5 <= avg_sentence_length <= 35:
                metrics['coherence_score'] = 0.7
            else:
                metrics['coherence_score'] = 0.4
            
            # Анализ полноты (наличие ключевых элементов)
            key_elements = ['что', 'как', 'когда', 'где', 'почему', 'который']
            found_elements = sum(1 for element in key_elements if element in response_text.lower())
            metrics['completeness_score'] = min(found_elements / len(key_elements), 1.0)
            
            # Анализ релевантности (на основе длины и структуры)
            word_count = len(response_text.split())
            if 50 <= word_count <= 500:  # Оптимальная длина ответа
                metrics['relevance_score'] = 1.0
            elif 20 <= word_count <= 1000:
                metrics['relevance_score'] = 0.7
            else:
                metrics['relevance_score'] = 0.4
            
            # Анализ точности (наличие конкретных данных)
            has_numbers = any(char.isdigit() for char in response_text)
            has_specific_terms = len([word for word in response_text.split() if len(word) > 5]) > 3
            
            if has_numbers and has_specific_terms:
                metrics['accuracy_score'] = 1.0
            elif has_numbers or has_specific_terms:
                metrics['accuracy_score'] = 0.7
            else:
                metrics['accuracy_score'] = 0.4
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing response quality: {e}")
            return {'coherence_score': 0.0, 'relevance_score': 0.0, 
                   'completeness_score': 0.0, 'accuracy_score': 0.0}
    
    async def record_search_quality(self, tenant_id: str, query_id: str, 
                                  query_text: str, results: List[Dict[str, Any]],
                                  user_feedback: Optional[str] = None) -> SearchQualityMetrics:
        """Запись метрик качества поиска"""
        try:
            # Расчет метрик
            relevance_score = self.calculate_relevance_score(query_text, results)
            precision_score = self.calculate_precision_score(query_text, results)
            
            # Для recall нужна информация о общем количестве релевантных документов
            # В реальной системе это должно приходить из внешней системы
            total_relevant_docs = len(results) * 2  # Примерная оценка
            recall_score = self.calculate_recall_score(query_text, results, total_relevant_docs)
            f1_score = self.calculate_f1_score(precision_score, recall_score)
            
            # Расчет качества ответа на основе результатов
            response_quality = relevance_score * 0.4 + precision_score * 0.3 + f1_score * 0.3
            
            metrics = SearchQualityMetrics(
                query_id=query_id,
                query_text=query_text,
                relevance_score=relevance_score,
                precision_score=precision_score,
                recall_score=recall_score,
                f1_score=f1_score,
                user_feedback=user_feedback,
                response_quality=response_quality
            )
            
            # Сохранение в ClickHouse
            await self._store_search_quality_metrics(tenant_id, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording search quality: {e}")
            return SearchQualityMetrics(
                query_id=query_id,
                query_text=query_text,
                relevance_score=0.0,
                precision_score=0.0,
                recall_score=0.0,
                f1_score=0.0
            )
    
    async def record_response_quality(self, tenant_id: str, response_id: str,
                                    response_text: str, response_time_ms: int,
                                    user_rating: Optional[int] = None) -> ResponseQualityMetrics:
        """Запись метрик качества ответа"""
        try:
            # Анализ качества ответа
            quality_metrics = self.analyze_response_quality(response_text)
            
            # Общая оценка качества
            overall_quality = (
                quality_metrics['coherence_score'] * 0.25 +
                quality_metrics['relevance_score'] * 0.25 +
                quality_metrics['completeness_score'] * 0.25 +
                quality_metrics['accuracy_score'] * 0.25
            )
            
            metrics = ResponseQualityMetrics(
                response_id=response_id,
                response_text=response_text,
                coherence_score=quality_metrics['coherence_score'],
                relevance_score=quality_metrics['relevance_score'],
                completeness_score=quality_metrics['completeness_score'],
                accuracy_score=quality_metrics['accuracy_score'],
                user_rating=user_rating,
                response_time_ms=response_time_ms
            )
            
            # Сохранение в ClickHouse
            await self._store_response_quality_metrics(tenant_id, metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording response quality: {e}")
            return ResponseQualityMetrics(
                response_id=response_id,
                response_text=response_text,
                coherence_score=0.0,
                relevance_score=0.0,
                completeness_score=0.0,
                accuracy_score=0.0,
                response_time_ms=response_time_ms
            )
    
    async def _store_search_quality_metrics(self, tenant_id: str, metrics: SearchQualityMetrics):
        """Сохранение метрик качества поиска в ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            data = {
                'timestamp': datetime.now(timezone.utc),
                'tenant_id': tenant_id,
                'query_id': metrics.query_id,
                'query_text': metrics.query_text,
                'relevance_score': metrics.relevance_score,
                'precision_score': metrics.precision_score,
                'recall_score': metrics.recall_score,
                'f1_score': metrics.f1_score,
                'user_feedback': metrics.user_feedback or '',
                'response_quality': metrics.response_quality
            }
            
            self.quality_buffer.append(data)
            
            # Записываем при достижении размера буфера
            if len(self.quality_buffer) >= self.buffer_size:
                await self._flush_quality_buffer()
                
        except Exception as e:
            logger.error(f"Error storing search quality metrics: {e}")
    
    async def _store_response_quality_metrics(self, tenant_id: str, metrics: ResponseQualityMetrics):
        """Сохранение метрик качества ответов в ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            # Здесь можно добавить отдельную таблицу для метрик ответов
            # Пока используем существующую структуру
            data = {
                'timestamp': datetime.now(timezone.utc),
                'tenant_id': tenant_id,
                'query_id': metrics.response_id,
                'query_text': metrics.response_text[:1000],  # Ограничиваем длину
                'relevance_score': metrics.relevance_score,
                'precision_score': metrics.coherence_score,
                'recall_score': metrics.completeness_score,
                'f1_score': metrics.accuracy_score,
                'user_feedback': str(metrics.user_rating) if metrics.user_rating else '',
                'response_quality': (
                    metrics.coherence_score * 0.25 +
                    metrics.relevance_score * 0.25 +
                    metrics.completeness_score * 0.25 +
                    metrics.accuracy_score * 0.25
                )
            }
            
            self.quality_buffer.append(data)
            
            # Записываем при достижении размера буфера
            if len(self.quality_buffer) >= self.buffer_size:
                await self._flush_quality_buffer()
                
        except Exception as e:
            logger.error(f"Error storing response quality metrics: {e}")
    
    async def _flush_quality_buffer(self):
        """Сброс буфера метрик качества в ClickHouse"""
        if not self.quality_buffer:
            return
        
        try:
            self.clickhouse_client.insert(
                'rag.search_quality_metrics',
                self.quality_buffer
            )
            self.quality_buffer.clear()
            logger.debug(f"Flushed {len(self.quality_buffer)} quality metrics to ClickHouse")
        except Exception as e:
            logger.error(f"Error flushing quality buffer: {e}")
    
    async def get_quality_statistics(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """Получение статистики качества за период"""
        if not self.clickhouse_client:
            return {}
        
        try:
            # Запрос статистики качества поиска
            query = """
            SELECT 
                avg(relevance_score) as avg_relevance,
                avg(precision_score) as avg_precision,
                avg(recall_score) as avg_recall,
                avg(f1_score) as avg_f1,
                avg(response_quality) as avg_response_quality,
                count() as total_queries
            FROM rag.search_quality_metrics
            WHERE tenant_id = %(tenant_id)s 
            AND timestamp >= now() - INTERVAL %(days)s DAY
            """
            
            result = self.clickhouse_client.query(
                query, 
                parameters={'tenant_id': tenant_id, 'days': days}
            )
            
            if result.result_rows:
                row = result.result_rows[0]
                return {
                    'avg_relevance': float(row[0]) if row[0] else 0.0,
                    'avg_precision': float(row[1]) if row[1] else 0.0,
                    'avg_recall': float(row[2]) if row[2] else 0.0,
                    'avg_f1': float(row[3]) if row[3] else 0.0,
                    'avg_response_quality': float(row[4]) if row[4] else 0.0,
                    'total_queries': int(row[5]) if row[5] else 0
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting quality statistics: {e}")
            return {}
    
    async def get_quality_trends(self, tenant_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Получение трендов качества по дням"""
        if not self.clickhouse_client:
            return []
        
        try:
            query = """
            SELECT 
                toDate(timestamp) as date,
                avg(relevance_score) as avg_relevance,
                avg(precision_score) as avg_precision,
                avg(f1_score) as avg_f1,
                count() as query_count
            FROM rag.search_quality_metrics
            WHERE tenant_id = %(tenant_id)s 
            AND timestamp >= now() - INTERVAL %(days)s DAY
            GROUP BY date
            ORDER BY date
            """
            
            result = self.clickhouse_client.query(
                query,
                parameters={'tenant_id': tenant_id, 'days': days}
            )
            
            trends = []
            for row in result.result_rows:
                trends.append({
                    'date': str(row[0]),
                    'avg_relevance': float(row[1]) if row[1] else 0.0,
                    'avg_precision': float(row[2]) if row[2] else 0.0,
                    'avg_f1': float(row[3]) if row[3] else 0.0,
                    'query_count': int(row[4]) if row[4] else 0
                })
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting quality trends: {e}")
            return []


# Глобальный экземпляр монитора качества
quality_monitor = QualityMonitor()


def get_quality_monitor() -> QualityMonitor:
    """Получение экземпляра монитора качества"""
    return quality_monitor
