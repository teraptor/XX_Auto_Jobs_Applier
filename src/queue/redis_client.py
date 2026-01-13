"""
Redis Client для асинхронного подключения к Redis
"""

import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper с автоматическим подключением и управлением соединением
    """

    def __init__(self, redis_url: str):
        """
        Инициализация Redis client

        Args:
            redis_url: Redis connection URL (redis://host:port или redis://host:port/db)
        """
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """
        Подключение к Redis

        Создает connection pool для эффективного управления соединениями
        """
        logger.info(f"Connecting to Redis: {self.redis_url}")

        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )

        # Проверка подключения
        await self.client.ping()

        logger.info("Redis connected successfully")

    async def close(self):
        """
        Закрытие соединения с Redis
        """
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """
        Проверка здоровья Redis соединения

        Returns:
            True если Redis доступен, False в противном случае
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def get_info(self) -> dict:
        """
        Получает информацию о Redis сервере

        Returns:
            Dict с информацией о Redis
        """
        try:
            info = await self.client.info()
            return info
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}

    async def flush_db(self):
        """
        Очищает текущую базу данных Redis

        Warning:
            Использовать только в development/testing!
        """
        logger.warning("Flushing Redis database")
        await self.client.flushdb()
