"""
Search Config Repository
Manages search configurations with JSONB storage
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg
import json

from .base import BaseRepository


class SearchConfigRepository(BaseRepository):
    """
    Repository for managing search configurations
    Uses JSONB for flexible config storage
    """

    async def create(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        config: Dict[str, Any],
        is_active: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new search config

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            name: Config name
            config: Search configuration as dictionary
            is_active: Whether this is the active config

        Returns:
            Created search config as dictionary
        """
        query = """
            INSERT INTO search_configs (
                tenant_id, user_id, name, config, is_active
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """

        # Convert dict to JSONB
        config_json = json.dumps(config)

        record = await self.fetchrow(
            query,
            tenant_id, user_id, name, config_json, is_active
        )

        return self.record_to_dict(record)

    async def get_by_id(
        self,
        config_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get search config by ID with tenant isolation

        Args:
            config_id: Config UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Search config dictionary or None
        """
        query = """
            SELECT * FROM search_configs
            WHERE id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, config_id, tenant_id)
        return self.record_to_dict(record)

    async def get_active(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get active search config for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            Active search config or None
        """
        query = """
            SELECT * FROM search_configs
            WHERE tenant_id = $1 AND user_id = $2 AND is_active = true
            LIMIT 1
        """

        record = await self.fetchrow(query, tenant_id, user_id)
        return self.record_to_dict(record)

    async def list_by_user(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all search configs for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of search configs
        """
        query = """
            SELECT * FROM search_configs
            WHERE tenant_id = $1 AND user_id = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
        """

        records = await self.fetch(query, tenant_id, user_id, limit, offset)
        return self.records_to_list(records)

    async def update_config(
        self,
        config_id: str,
        tenant_id: str,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update search config JSONB data

        Args:
            config_id: Config UUID
            tenant_id: Tenant UUID for isolation
            config: New configuration dictionary

        Returns:
            Updated search config or None
        """
        query = """
            UPDATE search_configs
            SET config = $3
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """

        config_json = json.dumps(config)

        record = await self.fetchrow(query, config_id, tenant_id, config_json)
        return self.record_to_dict(record)

    async def set_active(
        self,
        config_id: str,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Set a config as active (deactivates all others for this user)

        Args:
            config_id: Config UUID to activate
            tenant_id: Tenant UUID for isolation
            user_id: User UUID

        Returns:
            Activated search config or None
        """
        # Use transaction to deactivate all others first
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Deactivate all configs for this user
                await conn.execute(
                    """
                    UPDATE search_configs
                    SET is_active = false
                    WHERE tenant_id = $1 AND user_id = $2
                    """,
                    tenant_id, user_id
                )

                # Activate the specified config
                record = await conn.fetchrow(
                    """
                    UPDATE search_configs
                    SET is_active = true
                    WHERE id = $1 AND tenant_id = $2 AND user_id = $3
                    RETURNING *
                    """,
                    config_id, tenant_id, user_id
                )

        return self.record_to_dict(record)

    async def query_by_jsonb(
        self,
        tenant_id: str,
        user_id: str,
        json_path: str,
        value: Any
    ) -> List[Dict[str, Any]]:
        """
        Query configs by JSONB path

        Example:
            # Find configs where position is "Python Developer"
            query_by_jsonb(tenant_id, user_id, "position", "Python Developer")

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            json_path: JSONB path (e.g., "position" or "filters.experience")
            value: Value to match

        Returns:
            List of matching search configs
        """
        query = """
            SELECT * FROM search_configs
            WHERE tenant_id = $1 AND user_id = $2
            AND config->$3 = to_jsonb($4::text)
        """

        records = await self.fetch(query, tenant_id, user_id, json_path, str(value))
        return self.records_to_list(records)

    async def count_by_user(
        self,
        tenant_id: str,
        user_id: str
    ) -> int:
        """
        Count search configs for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            Count of search configs
        """
        query = """
            SELECT COUNT(*) FROM search_configs
            WHERE tenant_id = $1 AND user_id = $2
        """

        return await self.fetchval(query, tenant_id, user_id)

    async def delete(
        self,
        config_id: str,
        tenant_id: str
    ) -> bool:
        """
        Delete search config

        Args:
            config_id: Config UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM search_configs
            WHERE id = $1 AND tenant_id = $2
        """

        result = await self.execute(query, config_id, tenant_id)
        return "DELETE 1" in result
