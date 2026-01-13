"""
Base Repository Pattern
Provides common database operations for all repositories
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg


class BaseRepository:
    """
    Base class for all repositories
    Provides common CRUD operations with tenant isolation
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize repository with database pool

        Args:
            pool: asyncpg connection pool from DatabaseManager
        """
        self.pool = pool

    async def execute(
        self,
        query: str,
        *args,
        timeout: float = 10.0
    ) -> str:
        """
        Execute a query that doesn't return rows (INSERT, UPDATE, DELETE)

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Status string (e.g., "INSERT 0 1")
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def fetch(
        self,
        query: str,
        *args,
        timeout: float = 10.0
    ) -> List[asyncpg.Record]:
        """
        Fetch multiple rows

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            List of records
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchrow(
        self,
        query: str,
        *args,
        timeout: float = 10.0
    ) -> Optional[asyncpg.Record]:
        """
        Fetch a single row

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Single record or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def fetchval(
        self,
        query: str,
        *args,
        column: int = 0,
        timeout: float = 10.0
    ) -> Optional[Any]:
        """
        Fetch a single value

        Args:
            query: SQL query
            *args: Query parameters
            column: Column index to return
            timeout: Query timeout in seconds

        Returns:
            Single value or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)

    def record_to_dict(self, record: Optional[asyncpg.Record]) -> Optional[Dict[str, Any]]:
        """
        Convert asyncpg Record to dictionary

        Args:
            record: asyncpg Record or None

        Returns:
            Dictionary or None
        """
        if record is None:
            return None
        return dict(record)

    def records_to_list(self, records: List[asyncpg.Record]) -> List[Dict[str, Any]]:
        """
        Convert list of asyncpg Records to list of dictionaries

        Args:
            records: List of asyncpg Records

        Returns:
            List of dictionaries
        """
        return [dict(record) for record in records]
