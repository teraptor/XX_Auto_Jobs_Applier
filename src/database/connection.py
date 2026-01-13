"""
PostgreSQL Connection Pool для асинхронного доступа к БД

Использует asyncpg для высокопроизводительного асинхронного подключения.
Поддерживает connection pooling для эффективного использования ресурсов.
"""

import asyncpg
from typing import Optional
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager с connection pooling

    Управляет подключением к PostgreSQL через asyncpg.
    Создает pool соединений при старте приложения.
    """

    def __init__(self, database_url: str, min_size: int = 10, max_size: int = 50):
        """
        Инициализация Database Manager

        Args:
            database_url: PostgreSQL connection string
                          (postgresql://user:password@host:port/database)
            min_size: Минимальный размер connection pool
            max_size: Максимальный размер connection pool
        """
        self.database_url = database_url
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """
        Создание connection pool

        Создает pool асинхронных соединений с PostgreSQL.
        Рекомендуется вызывать при старте приложения.

        Raises:
            Exception: Если не удается подключиться к БД
        """
        if self.pool:
            logger.warning("Connection pool already exists")
            return

        logger.info(f"Connecting to PostgreSQL (min={self.min_size}, max={self.max_size})")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=60
            )

            # Проверка подключения
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                logger.info(f"PostgreSQL connected: {version}")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def close(self):
        """
        Закрытие connection pool

        Закрывает все соединения в pool.
        Рекомендуется вызывать при остановке приложения.
        """
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
            self.pool = None

    @asynccontextmanager
    async def acquire(self):
        """
        Context manager для получения соединения из pool

        Example:
            >>> async with db.acquire() as conn:
            >>>     result = await conn.fetch("SELECT * FROM users")
        """
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args) -> str:
        """
        Выполнить SQL команду (INSERT, UPDATE, DELETE)

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            Строка статуса выполнения

        Example:
            >>> await db.execute(
            >>>     "INSERT INTO users (name, email) VALUES ($1, $2)",
            >>>     "John", "john@example.com"
            >>> )
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Выполнить SELECT запрос и вернуть все строки

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            Список Record объектов

        Example:
            >>> rows = await db.fetch("SELECT * FROM users WHERE id = $1", user_id)
            >>> for row in rows:
            >>>     print(row['name'])
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Выполнить SELECT запрос и вернуть одну строку

        Args:
            query: SQL запрос
            *args: Параметры запроса

        Returns:
            Record объект или None

        Example:
            >>> row = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            >>> if row:
            >>>     print(row['name'])
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args, column: int = 0):
        """
        Выполнить SELECT запрос и вернуть одно значение

        Args:
            query: SQL запрос
            *args: Параметры запроса
            column: Индекс колонки (по умолчанию первая)

        Returns:
            Значение или None

        Example:
            >>> count = await db.fetchval("SELECT COUNT(*) FROM users")
            >>> print(f"Total users: {count}")
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column)

    async def health_check(self) -> bool:
        """
        Проверка здоровья подключения к БД

        Returns:
            True если БД доступна, False в противном случае
        """
        try:
            await self.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_pool_stats(self) -> dict:
        """
        Получить статистику connection pool

        Returns:
            Dict со статистикой pool
        """
        if not self.pool:
            return {"status": "not_connected"}

        return {
            "status": "connected",
            "size": self.pool.get_size(),
            "min_size": self.pool.get_min_size(),
            "max_size": self.pool.get_max_size(),
            "free_size": self.pool.get_idle_size()
        }


# Global database manager instance (для удобства)
db: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """
    Получить глобальный instance database manager

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: Если БД не инициализирована
    """
    if db is None:
        raise RuntimeError("Database is not initialized. Call init_db() first.")
    return db


async def init_db(database_url: str, min_size: int = 10, max_size: int = 50):
    """
    Инициализировать глобальный database manager

    Args:
        database_url: PostgreSQL connection string
        min_size: Минимальный размер pool
        max_size: Максимальный размер pool
    """
    global db
    db = DatabaseManager(database_url, min_size, max_size)
    await db.connect()


async def close_db():
    """Закрыть глобальный database manager"""
    global db
    if db:
        await db.close()
        db = None
