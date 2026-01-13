"""
Tenant Repository
Manages tenants for multi-tenant isolation
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg

from .base import BaseRepository


class TenantRepository(BaseRepository):
    """
    Repository for managing tenants
    Provides tenant CRUD operations and status management
    """

    async def create(
        self,
        name: str,
        slug: str,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create a new tenant

        Args:
            name: Tenant name
            slug: Unique slug for URL-friendly identifier
            status: Tenant status (active/suspended)

        Returns:
            Created tenant as dictionary

        Raises:
            asyncpg.UniqueViolationError: If slug already exists
        """
        query = """
            INSERT INTO tenants (name, slug, status)
            VALUES ($1, $2, $3)
            RETURNING *
        """

        record = await self.fetchrow(query, name, slug, status)
        return self.record_to_dict(record)

    async def get_by_id(
        self,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get tenant by ID

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant dictionary or None
        """
        query = """
            SELECT * FROM tenants
            WHERE id = $1
        """

        record = await self.fetchrow(query, tenant_id)
        return self.record_to_dict(record)

    async def get_by_slug(
        self,
        slug: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get tenant by slug

        Args:
            slug: Unique tenant slug

        Returns:
            Tenant dictionary or None
        """
        query = """
            SELECT * FROM tenants
            WHERE slug = $1
        """

        record = await self.fetchrow(query, slug)
        return self.record_to_dict(record)

    async def list_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all tenants with pagination

        Args:
            status: Filter by status (optional)
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of tenants
        """
        if status:
            query = """
                SELECT * FROM tenants
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            records = await self.fetch(query, status, limit, offset)
        else:
            query = """
                SELECT * FROM tenants
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            records = await self.fetch(query, limit, offset)

        return self.records_to_list(records)

    async def update_status(
        self,
        tenant_id: str,
        status: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update tenant status

        Args:
            tenant_id: Tenant UUID
            status: New status (active/suspended)

        Returns:
            Updated tenant or None
        """
        query = """
            UPDATE tenants
            SET status = $2
            WHERE id = $1
            RETURNING *
        """

        record = await self.fetchrow(query, tenant_id, status)
        return self.record_to_dict(record)

    async def update_name(
        self,
        tenant_id: str,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update tenant name

        Args:
            tenant_id: Tenant UUID
            name: New tenant name

        Returns:
            Updated tenant or None
        """
        query = """
            UPDATE tenants
            SET name = $2
            WHERE id = $1
            RETURNING *
        """

        record = await self.fetchrow(query, tenant_id, name)
        return self.record_to_dict(record)

    async def count_all(
        self,
        status: Optional[str] = None
    ) -> int:
        """
        Count all tenants

        Args:
            status: Filter by status (optional)

        Returns:
            Count of tenants
        """
        if status:
            query = """
                SELECT COUNT(*) FROM tenants
                WHERE status = $1
            """
            return await self.fetchval(query, status)
        else:
            query = """
                SELECT COUNT(*) FROM tenants
            """
            return await self.fetchval(query)

    async def delete(
        self,
        tenant_id: str
    ) -> bool:
        """
        Delete tenant (will cascade to all related data)

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM tenants
            WHERE id = $1
        """

        result = await self.execute(query, tenant_id)
        return "DELETE 1" in result
