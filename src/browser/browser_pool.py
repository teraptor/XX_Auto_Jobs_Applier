"""
Browser Pool Manager
Manages shared pool of Playwright browsers for multi-tenant use
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import uuid

from src.logger_config import logger


class BrowserInstance:
    """Represents a single browser instance in the pool"""

    def __init__(self, browser: Browser, browser_id: str):
        self.browser = browser
        self.browser_id = browser_id
        self.in_use = False
        self.current_tenant_id: Optional[str] = None
        self.current_user_id: Optional[str] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.created_at = datetime.utcnow()
        self.last_used_at = datetime.utcnow()
        self.total_uses = 0

    def mark_in_use(self, tenant_id: str, user_id: str):
        """Mark browser as in use"""
        self.in_use = True
        self.current_tenant_id = tenant_id
        self.current_user_id = user_id
        self.last_used_at = datetime.utcnow()
        self.total_uses += 1

    def mark_available(self):
        """Mark browser as available"""
        self.in_use = False
        self.current_tenant_id = None
        self.current_user_id = None

    async def cleanup_context(self):
        """Clean up browser context"""
        if self.page:
            try:
                await self.page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")
            self.page = None

        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
            self.context = None


class BrowserPool:
    """
    Shared browser pool for multi-tenant system
    Manages 5-10 Playwright browsers reused across tenants
    """

    def __init__(self, pool_size: int = 5, headless: bool = True):
        """
        Initialize browser pool

        Args:
            pool_size: Number of browsers in pool (5-10 recommended)
            headless: Run browsers in headless mode
        """
        self.pool_size = pool_size
        self.headless = headless
        self.browsers: List[BrowserInstance] = []
        self.playwright = None
        self.lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the browser pool"""
        if self._initialized:
            return

        logger.info(f"Initializing browser pool with {self.pool_size} browsers...")

        try:
            # Start Playwright
            self.playwright = await async_playwright().start()

            # Launch browsers
            for i in range(self.pool_size):
                browser_id = f"browser-{i+1}-{uuid.uuid4().hex[:8]}"

                browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                    ]
                )

                instance = BrowserInstance(browser, browser_id)
                self.browsers.append(instance)

                logger.info(f"  ✓ Launched browser {browser_id}")

            self._initialized = True
            logger.info(f"✅ Browser pool initialized with {len(self.browsers)} browsers")

        except Exception as e:
            logger.error(f"Failed to initialize browser pool: {e}")
            raise

    async def acquire(self, tenant_id: str, user_id: str, timeout: int = 60) -> BrowserInstance:
        """
        Acquire a browser from the pool

        Args:
            tenant_id: Tenant ID for tracking
            user_id: User ID for tracking
            timeout: Max wait time in seconds

        Returns:
            BrowserInstance

        Raises:
            TimeoutError: If no browser available within timeout
        """
        if not self._initialized:
            await self.initialize()

        start_time = asyncio.get_event_loop().time()

        while True:
            async with self.lock:
                # Find available browser
                for instance in self.browsers:
                    if not instance.in_use:
                        instance.mark_in_use(tenant_id, user_id)
                        logger.info(
                            f"Browser {instance.browser_id} acquired by "
                            f"tenant={tenant_id[:8]}... user={user_id[:8]}..."
                        )
                        return instance

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(
                    f"No browser available after {timeout}s. "
                    f"Pool size: {self.pool_size}, All in use."
                )

            # Wait a bit before retrying
            await asyncio.sleep(0.5)

    async def release(self, instance: BrowserInstance):
        """
        Release a browser back to the pool

        Args:
            instance: BrowserInstance to release
        """
        async with self.lock:
            # Clean up context
            await instance.cleanup_context()

            # Mark as available
            tenant_id = instance.current_tenant_id
            user_id = instance.current_user_id
            instance.mark_available()

            logger.info(
                f"Browser {instance.browser_id} released from "
                f"tenant={tenant_id[:8] if tenant_id else 'None'}... "
                f"user={user_id[:8] if user_id else 'None'}..."
            )

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Dictionary with pool stats
        """
        async with self.lock:
            in_use = sum(1 for b in self.browsers if b.in_use)
            available = len(self.browsers) - in_use

            total_uses = sum(b.total_uses for b in self.browsers)
            avg_uses = total_uses / len(self.browsers) if self.browsers else 0

            return {
                'pool_size': self.pool_size,
                'in_use': in_use,
                'available': available,
                'total_uses': total_uses,
                'avg_uses_per_browser': round(avg_uses, 2),
                'initialized': self._initialized
            }

    async def close(self):
        """Close all browsers and cleanup"""
        logger.info("Closing browser pool...")

        async with self.lock:
            for instance in self.browsers:
                try:
                    await instance.cleanup_context()
                    await instance.browser.close()
                    logger.info(f"  ✓ Closed browser {instance.browser_id}")
                except Exception as e:
                    logger.error(f"Error closing browser {instance.browser_id}: {e}")

            self.browsers.clear()

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self._initialized = False

        logger.info("✅ Browser pool closed")

    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()


class BrowserSession:
    """
    Context manager for using a browser from the pool
    Automatically acquires and releases browser
    """

    def __init__(self, pool: BrowserPool, tenant_id: str, user_id: str):
        """
        Initialize browser session

        Args:
            pool: BrowserPool instance
            tenant_id: Tenant ID
            user_id: User ID
        """
        self.pool = pool
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.instance: Optional[BrowserInstance] = None

    async def __aenter__(self) -> BrowserInstance:
        """Acquire browser from pool"""
        self.instance = await self.pool.acquire(self.tenant_id, self.user_id)
        return self.instance

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release browser back to pool"""
        if self.instance:
            await self.pool.release(self.instance)
