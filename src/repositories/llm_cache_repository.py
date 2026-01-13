"""
LLM Cache Repository
Manages LLM response caching with prompt hashing
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg
import json
import hashlib

from .base import BaseRepository


class LLMCacheRepository(BaseRepository):
    """
    Repository for managing LLM response cache
    Uses SHA256 hashing for prompt deduplication
    """

    @staticmethod
    def hash_prompt(prompt: str) -> str:
        """
        Generate SHA256 hash of prompt for caching

        Args:
            prompt: The prompt text

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    async def create(
        self,
        tenant_id: str,
        cache_key: str,
        prompt: str,
        response_data: Dict[str, Any],
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a new cache entry

        Args:
            tenant_id: Tenant UUID
            cache_key: Unique cache key
            prompt: Original prompt text
            response_data: LLM response as dictionary
            model_name: Model name used
            tokens_used: Total tokens used
            cost_usd: Cost in USD

        Returns:
            Created cache entry as dictionary

        Raises:
            asyncpg.UniqueViolationError: If cache_key already exists
        """
        query = """
            INSERT INTO llm_cache (
                tenant_id, cache_key, prompt_hash, response_data,
                model_name, tokens_used, cost_usd
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """

        prompt_hash = self.hash_prompt(prompt)
        response_json = json.dumps(response_data)

        record = await self.fetchrow(
            query,
            tenant_id, cache_key, prompt_hash, response_json,
            model_name, tokens_used, cost_usd
        )

        return self.record_to_dict(record)

    async def get_by_cache_key(
        self,
        tenant_id: str,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response by cache_key

        Args:
            tenant_id: Tenant UUID
            cache_key: Unique cache key

        Returns:
            Cache entry dictionary or None
        """
        query = """
            SELECT * FROM llm_cache
            WHERE tenant_id = $1 AND cache_key = $2
        """

        record = await self.fetchrow(query, tenant_id, cache_key)
        return self.record_to_dict(record)

    async def get_by_prompt_hash(
        self,
        tenant_id: str,
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response by prompt hash (for deduplication)

        Args:
            tenant_id: Tenant UUID
            prompt: Original prompt text

        Returns:
            Cache entry dictionary or None
        """
        query = """
            SELECT * FROM llm_cache
            WHERE tenant_id = $1 AND prompt_hash = $2
            ORDER BY created_at DESC
            LIMIT 1
        """

        prompt_hash = self.hash_prompt(prompt)

        record = await self.fetchrow(query, tenant_id, prompt_hash)
        return self.record_to_dict(record)

    async def list_by_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List cache entries for a tenant

        Args:
            tenant_id: Tenant UUID
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of cache entries
        """
        query = """
            SELECT * FROM llm_cache
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        records = await self.fetch(query, tenant_id, limit, offset)
        return self.records_to_list(records)

    async def get_stats(
        self,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get cache statistics for a tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with stats (total_entries, total_tokens, total_cost)
        """
        query = """
            SELECT
                COUNT(*) as total_entries,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM llm_cache
            WHERE tenant_id = $1
        """

        record = await self.fetchrow(query, tenant_id)

        return {
            'total_entries': record['total_entries'] or 0,
            'total_tokens': record['total_tokens'] or 0,
            'total_cost': float(record['total_cost'] or 0)
        }

    async def delete_old_entries(
        self,
        tenant_id: str,
        days_old: int = 30
    ) -> int:
        """
        Delete cache entries older than specified days

        Args:
            tenant_id: Tenant UUID
            days_old: Delete entries older than this many days

        Returns:
            Number of deleted entries
        """
        query = """
            DELETE FROM llm_cache
            WHERE tenant_id = $1
            AND created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
        """

        result = await self.execute(query % days_old, tenant_id)

        # Parse "DELETE N" to get count
        if "DELETE" in result:
            count = result.split()[1]
            return int(count)
        return 0

    async def delete(
        self,
        cache_id: str,
        tenant_id: str
    ) -> bool:
        """
        Delete cache entry

        Args:
            cache_id: Cache entry UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM llm_cache
            WHERE id = $1 AND tenant_id = $2
        """

        result = await self.execute(query, cache_id, tenant_id)
        return "DELETE 1" in result

    async def count_by_tenant(
        self,
        tenant_id: str
    ) -> int:
        """
        Count cache entries for a tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            Count of cache entries
        """
        query = """
            SELECT COUNT(*) FROM llm_cache
            WHERE tenant_id = $1
        """

        return await self.fetchval(query, tenant_id)
