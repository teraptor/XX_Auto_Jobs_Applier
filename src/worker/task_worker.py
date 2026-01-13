#!/usr/bin/env python3
"""
Task Worker
Processes tasks from Redis FIFO queue with Playwright automation
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger_config import logger
from src.queue.redis_client import RedisClient
from src.queue.task_queue import TaskQueue
from src.database.connection import DatabaseManager
from src.repositories import UserRepository, JobTaskRepository
from src.browser.browser_pool import BrowserPool, BrowserSession
from src.storage import TenantContext, StorageAdapter, CredentialsManager


class TaskWorker:
    """
    Worker that processes tasks from Redis FIFO queue
    Uses shared browser pool and multi-tenant storage
    """

    def __init__(
        self,
        redis_url: str,
        database_url: str,
        browser_pool_size: int = 5,
        headless: bool = True
    ):
        """
        Initialize task worker

        Args:
            redis_url: Redis connection URL
            database_url: PostgreSQL connection URL
            browser_pool_size: Number of browsers in pool
            headless: Run browsers in headless mode
        """
        self.redis_url = redis_url
        self.database_url = database_url
        self.browser_pool_size = browser_pool_size
        self.headless = headless

        # Components (initialized in start())
        self.redis_client: Optional[RedisClient] = None
        self.task_queue: Optional[TaskQueue] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.browser_pool: Optional[BrowserPool] = None

        # State
        self.running = False
        self.tasks_processed = 0
        self.tasks_succeeded = 0
        self.tasks_failed = 0

    async def start(self):
        """Start the worker"""
        logger.info("=" * 80)
        logger.info("Starting Task Worker")
        logger.info("=" * 80)

        try:
            # Initialize Redis
            logger.info("Connecting to Redis...")
            self.redis_client = RedisClient(self.redis_url)
            await self.redis_client.connect()
            self.task_queue = TaskQueue(self.redis_client)
            logger.info("✅ Connected to Redis")

            # Initialize Database
            logger.info("Connecting to PostgreSQL...")
            self.db_manager = DatabaseManager(self.database_url)
            await self.db_manager.connect()
            logger.info("✅ Connected to PostgreSQL")

            # Initialize Browser Pool
            logger.info(f"Initializing browser pool (size={self.browser_pool_size})...")
            self.browser_pool = BrowserPool(
                pool_size=self.browser_pool_size,
                headless=self.headless
            )
            await self.browser_pool.initialize()
            logger.info("✅ Browser pool initialized")

            # Start processing
            self.running = True
            logger.info("=" * 80)
            logger.info("Worker started successfully. Waiting for tasks...")
            logger.info("=" * 80)

            await self.process_loop()

        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.stop()

    async def stop(self):
        """Stop the worker"""
        logger.info("=" * 80)
        logger.info("Stopping Task Worker")
        logger.info("=" * 80)

        self.running = False

        # Close browser pool
        if self.browser_pool:
            await self.browser_pool.close()

        # Close database
        if self.db_manager:
            await self.db_manager.close()

        # Close Redis
        if self.redis_client:
            await self.redis_client.close()

        logger.info(f"Tasks processed: {self.tasks_processed}")
        logger.info(f"  ✅ Succeeded: {self.tasks_succeeded}")
        logger.info(f"  ❌ Failed: {self.tasks_failed}")
        logger.info("=" * 80)
        logger.info("Worker stopped")
        logger.info("=" * 80)

    async def process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Dequeue task with blocking timeout
                task_data = await self.task_queue.dequeue_task(timeout=5)

                if task_data:
                    await self.process_task(task_data)
                else:
                    # No task available, brief pause
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)

    async def process_task(self, task_data: Dict[str, Any]):
        """
        Process a single task

        Args:
            task_data: Task data from Redis queue
        """
        task_id = task_data.get('task_id')
        tenant_id = task_data.get('tenant_id')
        user_id = task_data.get('user_id')
        task_type = task_data.get('type', 'job_search_and_apply')

        logger.info("=" * 80)
        logger.info(f"Processing task: {task_id}")
        logger.info(f"  Tenant: {tenant_id[:8]}...")
        logger.info(f"  User: {user_id[:8]}...")
        logger.info(f"  Type: {task_type}")
        logger.info("=" * 80)

        self.tasks_processed += 1

        # Create tenant context
        context = TenantContext(tenant_id=tenant_id, user_id=user_id)

        # Create job task record in database
        job_task_repo = JobTaskRepository(self.db_manager.pool)

        try:
            await job_task_repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                task_id=task_id,
                task_type=task_type,
                payload=task_data,
                status="pending"
            )
        except Exception as e:
            logger.warning(f"Could not create job task record: {e}")

        # Update status to processing
        await self.task_queue.update_task_status(task_id, "processing")
        try:
            await job_task_repo.update_status(task_id, tenant_id, "processing")
        except:
            pass

        try:
            # Process task based on type
            if task_type == "job_search_and_apply":
                result = await self.process_job_search_and_apply(context, task_id)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            # Publish success result
            result_id = await self.task_queue.publish_result(
                task_id=task_id,
                status="completed",
                result_data=result
            )

            # Update database
            try:
                await job_task_repo.update_result(
                    task_id=task_id,
                    tenant_id=tenant_id,
                    result_id=result_id,
                    result=result,
                    status="completed"
                )
            except:
                pass

            self.tasks_succeeded += 1
            logger.info(f"✅ Task completed: {task_id} -> result_id: {result_id}")

        except Exception as e:
            error_message = str(e)
            error_traceback = traceback.format_exc()

            logger.error(f"❌ Task failed: {task_id}")
            logger.error(f"   Error: {error_message}")
            logger.error(error_traceback)

            # Publish failure result
            result_id = await self.task_queue.publish_result(
                task_id=task_id,
                status="failed",
                result_data={"error": error_message, "traceback": error_traceback}
            )

            # Update database
            try:
                await job_task_repo.update_result(
                    task_id=task_id,
                    tenant_id=tenant_id,
                    result_id=result_id,
                    result={"error": error_message},
                    status="failed"
                )
            except:
                pass

            self.tasks_failed += 1

    async def process_job_search_and_apply(
        self,
        context: TenantContext,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Process job search and apply task

        Args:
            context: Tenant context
            task_id: Task UUID

        Returns:
            Result data
        """
        logger.info(f"Starting job search and apply for tenant={context.tenant_id[:8]}...")

        # Initialize storage adapter
        storage = StorageAdapter(self.db_manager.pool, context)

        # Get credentials
        user_repo = UserRepository(self.db_manager.pool)
        creds_manager = CredentialsManager(user_repo, context)
        hh_login, hh_password = await creds_manager.get_hh_credentials()

        logger.info(f"  HH Login: {hh_login}")

        # Get search config
        search_config = await storage.get_search_config()
        if not search_config:
            raise ValueError("No active search config found")

        logger.info(f"  Search Config: {search_config.get('position', 'N/A')}")

        # Acquire browser from pool
        async with BrowserSession(self.browser_pool, context.tenant_id, context.user_id) as browser_instance:
            logger.info(f"  Browser: {browser_instance.browser_id}")

            # Create browser context
            browser_instance.context = await browser_instance.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            # Load saved session if available
            saved_session = await storage.get_browser_session()
            if saved_session:
                logger.info("  Restoring browser session from database")
                # TODO: Restore cookies and localStorage
                # await browser_instance.context.add_cookies(saved_session.get('cookies', []))

            # Create page
            browser_instance.page = await browser_instance.context.new_page()

            # TODO: Call existing job search and apply logic here
            # This is where you would integrate with:
            # - src/job_manager/job_applier.py
            # - src/job_manager/job_search.py
            #
            # For now, return a mock result

            applications_processed = 0
            applications_success = 0
            applications_failed = 0

            # Mock: Simulate processing
            await asyncio.sleep(2)

            # Save browser session
            # TODO: Extract cookies and localStorage
            # session_state = {
            #     'cookies': await browser_instance.context.cookies(),
            #     'localStorage': {}  # Extract from page
            # }
            # await storage.save_browser_session(session_state)

            result = {
                'task_id': task_id,
                'tenant_id': context.tenant_id,
                'user_id': context.user_id,
                'applications_processed': applications_processed,
                'applications_success': applications_success,
                'applications_failed': applications_failed,
                'completed_at': datetime.utcnow().isoformat(),
                'message': 'Job search and apply completed (mock implementation)'
            }

            logger.info(f"  ✅ Processed {applications_processed} applications")

            return result


async def main():
    """Main entry point"""
    # Get environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Get worker config
    browser_pool_size = int(os.getenv("BROWSER_POOL_SIZE", "5"))
    headless = os.getenv("HEADLESS", "true").lower() == "true"

    # Create and start worker
    worker = TaskWorker(
        redis_url=redis_url,
        database_url=database_url,
        browser_pool_size=browser_pool_size,
        headless=headless
    )

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
