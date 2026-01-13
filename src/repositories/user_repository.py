"""
User Repository
Manages users with HH.ru credentials encryption
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg

from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    Repository for managing users
    Includes HH.ru credentials with encryption support
    """

    async def create(
        self,
        tenant_id: str,
        email: str,
        hh_login: str,
        hh_password_encrypted: str,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new user

        Args:
            tenant_id: Tenant UUID
            email: User email
            hh_login: HH.ru login
            hh_password_encrypted: Encrypted HH.ru password
            is_active: Whether user is active

        Returns:
            Created user as dictionary

        Raises:
            asyncpg.UniqueViolationError: If user with email already exists
        """
        query = """
            INSERT INTO users (
                tenant_id, email, hh_login, hh_password_encrypted, is_active
            )
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """

        record = await self.fetchrow(
            query,
            tenant_id, email, hh_login, hh_password_encrypted, is_active
        )

        return self.record_to_dict(record)

    async def get_by_id(
        self,
        user_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by ID with tenant isolation

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            User dictionary or None
        """
        query = """
            SELECT * FROM users
            WHERE id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, user_id, tenant_id)
        return self.record_to_dict(record)

    async def get_by_email(
        self,
        tenant_id: str,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by email

        Args:
            tenant_id: Tenant UUID
            email: User email

        Returns:
            User dictionary or None
        """
        query = """
            SELECT * FROM users
            WHERE tenant_id = $1 AND email = $2
        """

        record = await self.fetchrow(query, tenant_id, email)
        return self.record_to_dict(record)

    async def list_by_tenant(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List users for a tenant with pagination

        Args:
            tenant_id: Tenant UUID
            is_active: Filter by active status (optional)
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of users
        """
        if is_active is not None:
            query = """
                SELECT * FROM users
                WHERE tenant_id = $1 AND is_active = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            records = await self.fetch(query, tenant_id, is_active, limit, offset)
        else:
            query = """
                SELECT * FROM users
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            records = await self.fetch(query, tenant_id, limit, offset)

        return self.records_to_list(records)

    async def update_credentials(
        self,
        user_id: str,
        tenant_id: str,
        hh_login: str,
        hh_password_encrypted: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update HH.ru credentials

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID for isolation
            hh_login: New HH.ru login
            hh_password_encrypted: New encrypted password

        Returns:
            Updated user or None
        """
        query = """
            UPDATE users
            SET hh_login = $3, hh_password_encrypted = $4
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """

        record = await self.fetchrow(
            query,
            user_id, tenant_id, hh_login, hh_password_encrypted
        )
        return self.record_to_dict(record)

    async def update_active_status(
        self,
        user_id: str,
        tenant_id: str,
        is_active: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Update user active status

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID for isolation
            is_active: New active status

        Returns:
            Updated user or None
        """
        query = """
            UPDATE users
            SET is_active = $3
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """

        record = await self.fetchrow(query, user_id, tenant_id, is_active)
        return self.record_to_dict(record)

    async def count_by_tenant(
        self,
        tenant_id: str,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count users for a tenant

        Args:
            tenant_id: Tenant UUID
            is_active: Filter by active status (optional)

        Returns:
            Count of users
        """
        if is_active is not None:
            query = """
                SELECT COUNT(*) FROM users
                WHERE tenant_id = $1 AND is_active = $2
            """
            return await self.fetchval(query, tenant_id, is_active)
        else:
            query = """
                SELECT COUNT(*) FROM users
                WHERE tenant_id = $1
            """
            return await self.fetchval(query, tenant_id)

    async def delete(
        self,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """
        Delete user (will cascade to related records)

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM users
            WHERE id = $1 AND tenant_id = $2
        """

        result = await self.execute(query, user_id, tenant_id)
        return "DELETE 1" in result
