"""
Browser Session Repository
Manages Playwright browser sessions with JSONB state storage
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg
import json

from .base import BaseRepository


class BrowserSessionRepository(BaseRepository):
    """
    Repository for managing browser sessions
    Stores Playwright session state (cookies, localStorage) in JSONB
    """

    async def create_or_update(
        self,
        tenant_id: str,
        user_id: str,
        session_state: Dict[str, Any],
        is_valid: bool = True
    ) -> Dict[str, Any]:
        """
        Create or update browser session (upsert)
        Uses unique constraint on (tenant_id, user_id)

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            session_state: Playwright session state (cookies, localStorage)
            is_valid: Whether session is still valid

        Returns:
            Created/updated browser session as dictionary
        """
        query = """
            INSERT INTO browser_sessions (
                tenant_id, user_id, session_state, is_valid, last_validated_at
            )
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            ON CONFLICT (tenant_id, user_id)
            DO UPDATE SET
                session_state = EXCLUDED.session_state,
                is_valid = EXCLUDED.is_valid,
                last_validated_at = CURRENT_TIMESTAMP
            RETURNING *
        """

        session_json = json.dumps(session_state)

        record = await self.fetchrow(
            query,
            tenant_id, user_id, session_json, is_valid
        )

        return self.record_to_dict(record)

    async def get_by_user(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get browser session for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            Browser session dictionary or None
        """
        query = """
            SELECT * FROM browser_sessions
            WHERE tenant_id = $1 AND user_id = $2
        """

        record = await self.fetchrow(query, tenant_id, user_id)
        return self.record_to_dict(record)

    async def get_valid_sessions(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all valid sessions for a tenant

        Args:
            tenant_id: Tenant UUID
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of valid browser sessions
        """
        query = """
            SELECT * FROM browser_sessions
            WHERE tenant_id = $1 AND is_valid = true
            ORDER BY last_validated_at DESC
            LIMIT $2 OFFSET $3
        """

        records = await self.fetch(query, tenant_id, limit, offset)
        return self.records_to_list(records)

    async def invalidate_session(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Mark session as invalid

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            Updated browser session or None
        """
        query = """
            UPDATE browser_sessions
            SET is_valid = false
            WHERE tenant_id = $1 AND user_id = $2
            RETURNING *
        """

        record = await self.fetchrow(query, tenant_id, user_id)
        return self.record_to_dict(record)

    async def update_validation_time(
        self,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update last_validated_at timestamp

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            Updated browser session or None
        """
        query = """
            UPDATE browser_sessions
            SET last_validated_at = CURRENT_TIMESTAMP
            WHERE tenant_id = $1 AND user_id = $2
            RETURNING *
        """

        record = await self.fetchrow(query, tenant_id, user_id)
        return self.record_to_dict(record)

    async def delete(
        self,
        tenant_id: str,
        user_id: str
    ) -> bool:
        """
        Delete browser session

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM browser_sessions
            WHERE tenant_id = $1 AND user_id = $2
        """

        result = await self.execute(query, tenant_id, user_id)
        return "DELETE 1" in result

    async def count_valid_sessions(
        self,
        tenant_id: str
    ) -> int:
        """
        Count valid sessions for a tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            Count of valid sessions
        """
        query = """
            SELECT COUNT(*) FROM browser_sessions
            WHERE tenant_id = $1 AND is_valid = true
        """

        return await self.fetchval(query, tenant_id)
