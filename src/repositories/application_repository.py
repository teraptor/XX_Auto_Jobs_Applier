"""
Application Repository
Manages job applications with task_id tracking
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg

from .base import BaseRepository


class ApplicationRepository(BaseRepository):
    """
    Repository for managing job applications
    Includes task_id for Redis Queue integration
    """

    async def create(
        self,
        tenant_id: str,
        user_id: str,
        vacancy_id: str,
        task_id: Optional[str] = None,
        vacancy_url: Optional[str] = None,
        company_name: Optional[str] = None,
        position_title: Optional[str] = None,
        status: str = "pending",
        cover_letter: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new application record

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            vacancy_id: Vacancy ID from HH.ru
            task_id: Task UUID from Redis Queue (optional)
            vacancy_url: URL to vacancy
            company_name: Company name
            position_title: Job position title
            status: Application status (pending/success/failed/skipped)
            cover_letter: Generated cover letter
            error_message: Error message if failed

        Returns:
            Created application as dictionary

        Raises:
            asyncpg.UniqueViolationError: If application already exists
        """
        query = """
            INSERT INTO applications (
                tenant_id, user_id, vacancy_id, task_id,
                vacancy_url, company_name, position_title,
                status, cover_letter, error_message
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """

        record = await self.fetchrow(
            query,
            tenant_id, user_id, vacancy_id, task_id,
            vacancy_url, company_name, position_title,
            status, cover_letter, error_message
        )

        return self.record_to_dict(record)

    async def get_by_id(
        self,
        application_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get application by ID with tenant isolation

        Args:
            application_id: Application UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Application dictionary or None
        """
        query = """
            SELECT * FROM applications
            WHERE id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, application_id, tenant_id)
        return self.record_to_dict(record)

    async def get_by_vacancy(
        self,
        tenant_id: str,
        user_id: str,
        vacancy_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get application by vacancy_id (check if already applied)

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            vacancy_id: Vacancy ID from HH.ru

        Returns:
            Application dictionary or None
        """
        query = """
            SELECT * FROM applications
            WHERE tenant_id = $1 AND user_id = $2 AND vacancy_id = $3
        """

        record = await self.fetchrow(query, tenant_id, user_id, vacancy_id)
        return self.record_to_dict(record)

    async def get_by_task_id(
        self,
        task_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get application by task_id from Redis Queue

        Args:
            task_id: Task UUID from Redis
            tenant_id: Tenant UUID for isolation

        Returns:
            Application dictionary or None
        """
        query = """
            SELECT * FROM applications
            WHERE task_id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, task_id, tenant_id)
        return self.record_to_dict(record)

    async def list_by_user(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List applications for a user with pagination

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            limit: Max number of records
            offset: Offset for pagination
            status: Filter by status (optional)

        Returns:
            List of applications
        """
        if status:
            query = """
                SELECT * FROM applications
                WHERE tenant_id = $1 AND user_id = $2 AND status = $3
                ORDER BY applied_at DESC
                LIMIT $4 OFFSET $5
            """
            records = await self.fetch(query, tenant_id, user_id, status, limit, offset)
        else:
            query = """
                SELECT * FROM applications
                WHERE tenant_id = $1 AND user_id = $2
                ORDER BY applied_at DESC
                LIMIT $3 OFFSET $4
            """
            records = await self.fetch(query, tenant_id, user_id, limit, offset)

        return self.records_to_list(records)

    async def update_status(
        self,
        application_id: str,
        tenant_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update application status

        Args:
            application_id: Application UUID
            tenant_id: Tenant UUID for isolation
            status: New status (success/failed/skipped)
            error_message: Error message if failed

        Returns:
            Updated application or None
        """
        query = """
            UPDATE applications
            SET status = $3, error_message = $4
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """

        record = await self.fetchrow(query, application_id, tenant_id, status, error_message)
        return self.record_to_dict(record)

    async def count_by_user(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> int:
        """
        Count applications for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            status: Filter by status (optional)

        Returns:
            Count of applications
        """
        if status:
            query = """
                SELECT COUNT(*) FROM applications
                WHERE tenant_id = $1 AND user_id = $2 AND status = $3
            """
            return await self.fetchval(query, tenant_id, user_id, status)
        else:
            query = """
                SELECT COUNT(*) FROM applications
                WHERE tenant_id = $1 AND user_id = $2
            """
            return await self.fetchval(query, tenant_id, user_id)

    async def delete(
        self,
        application_id: str,
        tenant_id: str
    ) -> bool:
        """
        Delete application

        Args:
            application_id: Application UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM applications
            WHERE id = $1 AND tenant_id = $2
        """

        result = await self.execute(query, application_id, tenant_id)
        return "DELETE 1" in result
