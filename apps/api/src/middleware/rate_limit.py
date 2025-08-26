"""
Middleware для rate limiting
"""
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
import logging

from ..services.cache import cache_service
from ..schemas.auth import RateLimitInfo

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self, 
                 requests_per_minute: int = 60,
                 requests_per_hour: int = 1000,
                 requests_per_day: int = 10000,
                 burst_limit: int = 10):
        """
        Инициализация rate limiting
        
        Args:
            requests_per_minute: Запросов в минуту
            requests_per_hour: Запросов в час
            requests_per_day: Запросов в день
            burst_limit: Лимит всплесков (запросов подряд)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
    
    async def __call__(self, request: Request):
        """
        Обработка запроса с проверкой rate limiting
        
        Args:
            request: FastAPI запрос
        """
        # Получаем идентификатор клиента
        client_id = self._get_client_id(request)
        
        # Проверяем rate limiting
        rate_limit_info = await self._check_rate_limit(client_id, request.url.path)
        
        # Добавляем информацию о rate limiting в заголовки
        request.state.rate_limit_info = rate_limit_info
        
        # Если превышен лимит, возвращаем ошибку
        if rate_limit_info.remaining <= 0:
            reset_time = rate_limit_info.reset_time.strftime("%Y-%m-%d %H:%M:%S")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Превышен лимит запросов. Попробуйте после {reset_time}",
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info.limit),
                    "X-RateLimit-Remaining": str(rate_limit_info.remaining),
                    "X-RateLimit-Reset": reset_time,
                    "Retry-After": str(int((rate_limit_info.reset_time.timestamp() - time.time())))
                }
            )
        
        # Добавляем заголовки rate limiting в ответ
        response = await self._process_request(request)
        
        # Добавляем заголовки rate limiting
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = rate_limit_info.reset_time.strftime("%Y-%m-%d %H:%M:%S")
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Получение идентификатора клиента
        
        Args:
            request: FastAPI запрос
            
        Returns:
            Идентификатор клиента
        """
        # Приоритет: API ключ, JWT токен, IP адрес
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key}"
        
        # Пробуем получить пользователя из JWT токена
        try:
            from ..middleware.auth import get_current_user
            user = get_current_user(request)
            return f"user:{user.user_id}"
        except:
            pass
        
        # Используем IP адрес
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitInfo:
        """
        Проверка rate limiting для клиента и эндпоинта
        
        Args:
            client_id: Идентификатор клиента
            endpoint: Эндпоинт API
            
        Returns:
            Информация о rate limiting
        """
        current_time = time.time()
        
        # Ключи для разных временных интервалов
        minute_key = f"rate_limit:{client_id}:{endpoint}:minute:{int(current_time / 60)}"
        hour_key = f"rate_limit:{client_id}:{endpoint}:hour:{int(current_time / 3600)}"
        day_key = f"rate_limit:{client_id}:{endpoint}:day:{int(current_time / 86400)}"
        burst_key = f"rate_limit:{client_id}:{endpoint}:burst"
        
        # Проверяем burst limit
        burst_count = await cache_service.get(burst_key, 0)
        if burst_count >= self.burst_limit:
            # Слишком много запросов подряд, ждем
            await cache_service.set(burst_key, burst_count, 60)  # 1 минута
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов подряд. Подождите немного."
            )
        
        # Увеличиваем счетчики
        minute_count = await cache_service.increment(minute_key, 1) or 1
        hour_count = await cache_service.increment(hour_key, 1) or 1
        day_count = await cache_service.increment(day_key, 1) or 1
        burst_count = await cache_service.increment(burst_key, 1) or 1
        
        # Устанавливаем TTL для ключей
        await cache_service.expire(minute_key, 60)  # 1 минута
        await cache_service.expire(hour_key, 3600)  # 1 час
        await cache_service.expire(day_key, 86400)  # 1 день
        await cache_service.expire(burst_key, 60)  # 1 минута для burst
        
        # Определяем лимит и оставшиеся запросы
        if minute_count > self.requests_per_minute:
            limit = self.requests_per_minute
            remaining = 0
            reset_time = current_time + 60 - (current_time % 60)
        elif hour_count > self.requests_per_hour:
            limit = self.requests_per_hour
            remaining = 0
            reset_time = current_time + 3600 - (current_time % 3600)
        elif day_count > self.requests_per_day:
            limit = self.requests_per_day
            remaining = 0
            reset_time = current_time + 86400 - (current_time % 86400)
        else:
            # Определяем ближайший лимит
            if minute_count >= self.requests_per_minute:
                limit = self.requests_per_minute
                remaining = 0
                reset_time = current_time + 60 - (current_time % 60)
            elif hour_count >= self.requests_per_hour:
                limit = self.requests_per_hour
                remaining = self.requests_per_hour - hour_count
                reset_time = current_time + 3600 - (current_time % 3600)
            elif day_count >= self.requests_per_day:
                limit = self.requests_per_day
                remaining = self.requests_per_day - day_count
                reset_time = current_time + 86400 - (current_time % 86400)
            else:
                # Используем минутный лимит как основной
                limit = self.requests_per_minute
                remaining = self.requests_per_minute - minute_count
                reset_time = current_time + 60 - (current_time % 60)
        
        from datetime import datetime
        return RateLimitInfo(
            remaining=remaining,
            reset_time=datetime.fromtimestamp(reset_time),
            limit=limit
        )
    
    async def _process_request(self, request: Request):
        """
        Обработка запроса (заглушка для совместимости)
        
        Args:
            request: FastAPI запрос
            
        Returns:
            Ответ (будет переопределен в реальном использовании)
        """
        # В реальном использовании этот метод будет переопределен
        # Здесь просто возвращаем None для совместимости
        return None


def rate_limit(requests_per_minute: int = 60,
               requests_per_hour: int = 1000,
               requests_per_day: int = 10000,
               burst_limit: int = 10):
    """
    Декоратор для применения rate limiting к эндпоинтам
    
    Args:
        requests_per_minute: Запросов в минуту
        requests_per_hour: Запросов в час
        requests_per_day: Запросов в день
        burst_limit: Лимит всплесков
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Получаем request из аргументов
            request = None
            for arg in args:
                if hasattr(arg, '__class__') and arg.__class__.__name__ == 'Request':
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if hasattr(value, '__class__') and value.__class__.__name__ == 'Request':
                        request = value
                        break
            
            if not request:
                # Если не можем найти request, пропускаем rate limiting
                return await func(*args, **kwargs)
            
            # Применяем rate limiting
            rate_limiter = RateLimitMiddleware(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
                requests_per_day=requests_per_day,
                burst_limit=burst_limit
            )
            
            # Проверяем rate limit
            await rate_limiter._check_rate_limit(
                rate_limiter._get_client_id(request),
                request.url.path
            )
            
            # Если все в порядке, выполняем функцию
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
