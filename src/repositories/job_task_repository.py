"""
Job Task Repository
Manages job tasks with task_id and result_id tracking
Long-term storage supplementing Redis TTL
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncpg
import json

from .base import BaseRepository


class JobTaskRepository(BaseRepository):
    """
    Repository for managing job tasks
    Stores long-term history with task_id (input) and result_id (output) tracking
    """

    async def create(
        self,
        tenant_id: str,
        user_id: str,
        task_id: str,
        task_type: str = "job_search_and_apply",
        payload: Optional[Dict[str, Any]] = None,
        status: str = "pending"
    ) -> Dict[str, Any]:
        """
        Create a new job task record

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            task_id: Task UUID from Redis Queue
            task_type: Type of task
            payload: Task payload as dictionary
            status: Initial status (pending/processing/completed/failed)

        Returns:
            Created job task as dictionary

        Raises:
            asyncpg.UniqueViolationError: If task_id already exists
        """
        query = """
            INSERT INTO job_tasks (
                tenant_id, user_id, task_id, task_type, payload, status
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """

        payload_json = json.dumps(payload) if payload else None

        record = await self.fetchrow(
            query,
            tenant_id, user_id, task_id, task_type, payload_json, status
        )

        return self.record_to_dict(record)

    async def get_by_task_id(
        self,
        task_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get job task by task_id with tenant isolation

        Args:
            task_id: Task UUID from Redis
            tenant_id: Tenant UUID for isolation

        Returns:
            Job task dictionary or None
        """
        query = """
            SELECT * FROM job_tasks
            WHERE task_id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, task_id, tenant_id)
        return self.record_to_dict(record)

    async def get_by_result_id(
        self,
        result_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get job task by result_id (reverse lookup)

        Args:
            result_id: Result UUID from Redis
            tenant_id: Tenant UUID for isolation

        Returns:
            Job task dictionary or None
        """
        query = """
            SELECT * FROM job_tasks
            WHERE result_id = $1 AND tenant_id = $2
        """

        record = await self.fetchrow(query, result_id, tenant_id)
        return self.record_to_dict(record)

    async def update_status(
        self,
        task_id: str,
        tenant_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update task status

        Args:
            task_id: Task UUID
            tenant_id: Tenant UUID for isolation
            status: New status (processing/completed/failed)
            started_at: Timestamp when task started
            error_message: Error message if failed

        Returns:
            Updated job task or None
        """
        if status == "processing":
            query = """
                UPDATE job_tasks
                SET status = $3, started_at = COALESCE($4, CURRENT_TIMESTAMP)
                WHERE task_id = $1 AND tenant_id = $2
                RETURNING *
            """
            record = await self.fetchrow(query, task_id, tenant_id, status, started_at)
        elif status in ["completed", "failed"]:
            query = """
                UPDATE job_tasks
                SET status = $3,
                    completed_at = CURRENT_TIMESTAMP,
                    error_message = $4
                WHERE task_id = $1 AND tenant_id = $2
                RETURNING *
            """
            record = await self.fetchrow(query, task_id, tenant_id, status, error_message)
        else:
            query = """
                UPDATE job_tasks
                SET status = $3
                WHERE task_id = $1 AND tenant_id = $2
                RETURNING *
            """
            record = await self.fetchrow(query, task_id, tenant_id, status)

        return self.record_to_dict(record)

    async def update_result(
        self,
        task_id: str,
        tenant_id: str,
        result_id: str,
        result: Dict[str, Any],
        status: str = "completed"
    ) -> Optional[Dict[str, Any]]:
        """
        Update task with result_id and result data

        Args:
            task_id: Task UUID
            tenant_id: Tenant UUID for isolation
            result_id: Result UUID from Redis
            result: Result data as dictionary
            status: Final status (completed/failed)

        Returns:
            Updated job task or None
        """
        query = """
            UPDATE job_tasks
            SET result_id = $3,
                result = $4,
                status = $5,
                completed_at = CURRENT_TIMESTAMP
            WHERE task_id = $1 AND tenant_id = $2
            RETURNING *
        """

        result_json = json.dumps(result)

        record = await self.fetchrow(
            query,
            task_id, tenant_id, result_id, result_json, status
        )

        return self.record_to_dict(record)

    async def list_by_user(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List job tasks for a user with pagination

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            status: Filter by status (optional)
            limit: Max number of records
            offset: Offset for pagination

        Returns:
            List of job tasks
        """
        if status:
            query = """
                SELECT * FROM job_tasks
                WHERE tenant_id = $1 AND user_id = $2 AND status = $3
                ORDER BY created_at DESC
                LIMIT $4 OFFSET $5
            """
            records = await self.fetch(query, tenant_id, user_id, status, limit, offset)
        else:
            query = """
                SELECT * FROM job_tasks
                WHERE tenant_id = $1 AND user_id = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            records = await self.fetch(query, tenant_id, user_id, limit, offset)

        return self.records_to_list(records)

    async def get_pending_tasks(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get pending tasks for a tenant

        Args:
            tenant_id: Tenant UUID
            limit: Max number of records

        Returns:
            List of pending job tasks
        """
        query = """
            SELECT * FROM job_tasks
            WHERE tenant_id = $1 AND status = 'pending'
            ORDER BY created_at ASC
            LIMIT $2
        """

        records = await self.fetch(query, tenant_id, limit)
        return self.records_to_list(records)

    async def get_stats(
        self,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get task statistics

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID (optional, for per-user stats)

        Returns:
            Dictionary with stats (total, pending, processing, completed, failed)
        """
        if user_id:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM job_tasks
                WHERE tenant_id = $1 AND user_id = $2
            """
            record = await self.fetchrow(query, tenant_id, user_id)
        else:
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM job_tasks
                WHERE tenant_id = $1
            """
            record = await self.fetchrow(query, tenant_id)

        return {
            'total': record['total'] or 0,
            'pending': record['pending'] or 0,
            'processing': record['processing'] or 0,
            'completed': record['completed'] or 0,
            'failed': record['failed'] or 0
        }

    async def delete_old_tasks(
        self,
        tenant_id: str,
        days_old: int = 90
    ) -> int:
        """
        Delete tasks older than specified days

        Args:
            tenant_id: Tenant UUID
            days_old: Delete tasks older than this many days

        Returns:
            Number of deleted tasks
        """
        query = """
            DELETE FROM job_tasks
            WHERE tenant_id = $1
            AND created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
        """

        result = await self.execute(query % days_old, tenant_id)

        # Parse "DELETE N" to get count
        if "DELETE" in result:
            count = result.split()[1]
            return int(count)
        return 0

    async def count_by_user(
        self,
        tenant_id: str,
        user_id: str,
        status: Optional[str] = None
    ) -> int:
        """
        Count tasks for a user

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            status: Filter by status (optional)

        Returns:
            Count of tasks
        """
        if status:
            query = """
                SELECT COUNT(*) FROM job_tasks
                WHERE tenant_id = $1 AND user_id = $2 AND status = $3
            """
            return await self.fetchval(query, tenant_id, user_id, status)
        else:
            query = """
                SELECT COUNT(*) FROM job_tasks
                WHERE tenant_id = $1 AND user_id = $2
            """
            return await self.fetchval(query, tenant_id, user_id)
