"""
Storage Adapter
Provides database-backed storage interface compatible with existing YAML code
Minimal changes to existing codebase
"""
from typing import Optional, Dict, Any
from pathlib import Path
import asyncpg

from src.repositories import (
    SearchConfigRepository,
    ApplicationRepository,
    BrowserSessionRepository,
    LLMCacheRepository
)
from src.storage.tenant_context import TenantContext


class StorageAdapter:
    """
    Adapter for multi-tenant storage operations
    Wraps database repositories to provide YAML-like interface
    """

    def __init__(self, pool: asyncpg.Pool, context: TenantContext):
        """
        Initialize storage adapter

        Args:
            pool: Database connection pool
            context: Tenant context for isolation
        """
        self.pool = pool
        self.context = context

        # Initialize repositories
        self.search_config_repo = SearchConfigRepository(pool)
        self.application_repo = ApplicationRepository(pool)
        self.browser_session_repo = BrowserSessionRepository(pool)
        self.llm_cache_repo = LLMCacheRepository(pool)

    async def get_search_config(self) -> Optional[Dict[str, Any]]:
        """
        Get active search config for current tenant/user
        Replaces: load_yaml_file(Path("data_folder/search_config.yaml"))

        Returns:
            Search config dictionary or None
        """
        config = await self.search_config_repo.get_active(
            self.context.tenant_id,
            self.context.user_id
        )

        if config:
            # Return just the config JSONB data
            return config['config']

        return None

    async def save_application(
        self,
        vacancy_id: str,
        vacancy_url: Optional[str] = None,
        company_name: Optional[str] = None,
        position_title: Optional[str] = None,
        status: str = "success",
        cover_letter: Optional[str] = None,
        error_message: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save application to database
        Replaces: Writing to data_folder/output/applications.yaml

        Args:
            vacancy_id: HH.ru vacancy ID
            vacancy_url: URL to vacancy
            company_name: Company name
            position_title: Job position
            status: success|failed|skipped
            cover_letter: Generated cover letter
            error_message: Error if failed
            task_id: Task UUID from Redis Queue

        Returns:
            Created application record
        """
        # Check if already applied
        existing = await self.application_repo.get_by_vacancy(
            self.context.tenant_id,
            self.context.user_id,
            vacancy_id
        )

        if existing:
            # Already applied, return existing
            return existing

        # Create new application
        application = await self.application_repo.create(
            tenant_id=self.context.tenant_id,
            user_id=self.context.user_id,
            vacancy_id=vacancy_id,
            task_id=task_id,
            vacancy_url=vacancy_url,
            company_name=company_name,
            position_title=position_title,
            status=status,
            cover_letter=cover_letter,
            error_message=error_message
        )

        return application

    async def is_already_applied(self, vacancy_id: str) -> bool:
        """
        Check if already applied to this vacancy
        Replaces: Checking applications.yaml

        Args:
            vacancy_id: HH.ru vacancy ID

        Returns:
            True if already applied
        """
        application = await self.application_repo.get_by_vacancy(
            self.context.tenant_id,
            self.context.user_id,
            vacancy_id
        )

        return application is not None

    async def get_browser_session(self) -> Optional[Dict[str, Any]]:
        """
        Get browser session state
        Replaces: Loading Playwright state from file

        Returns:
            Session state dictionary or None
        """
        session = await self.browser_session_repo.get_by_user(
            self.context.tenant_id,
            self.context.user_id
        )

        if session and session['is_valid']:
            # Return just the session_state JSONB data
            return session['session_state']

        return None

    async def save_browser_session(self, session_state: Dict[str, Any]) -> None:
        """
        Save browser session state
        Replaces: Saving Playwright state to file

        Args:
            session_state: Playwright session (cookies, localStorage)
        """
        await self.browser_session_repo.create_or_update(
            tenant_id=self.context.tenant_id,
            user_id=self.context.user_id,
            session_state=session_state,
            is_valid=True
        )

    async def invalidate_browser_session(self) -> None:
        """Mark browser session as invalid"""
        await self.browser_session_repo.invalidate_session(
            self.context.tenant_id,
            self.context.user_id
        )

    async def get_llm_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response
        Replaces: LLM in-memory cache

        Args:
            cache_key: Unique cache key

        Returns:
            Cached response data or None
        """
        cache_entry = await self.llm_cache_repo.get_by_cache_key(
            self.context.tenant_id,
            cache_key
        )

        if cache_entry:
            return cache_entry['response_data']

        return None

    async def get_llm_cache_by_prompt(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response by prompt hash
        For deduplication of identical prompts

        Args:
            prompt: The prompt text

        Returns:
            Cached response data or None
        """
        cache_entry = await self.llm_cache_repo.get_by_prompt_hash(
            self.context.tenant_id,
            prompt
        )

        if cache_entry:
            return cache_entry['response_data']

        return None

    async def save_llm_cache(
        self,
        cache_key: str,
        prompt: str,
        response_data: Dict[str, Any],
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None
    ) -> None:
        """
        Save LLM response to cache
        Replaces: In-memory LLM cache

        Args:
            cache_key: Unique cache key
            prompt: Original prompt
            response_data: LLM response
            model_name: Model used
            tokens_used: Tokens consumed
            cost_usd: Cost in USD
        """
        try:
            await self.llm_cache_repo.create(
                tenant_id=self.context.tenant_id,
                cache_key=cache_key,
                prompt=prompt,
                response_data=response_data,
                model_name=model_name,
                tokens_used=tokens_used,
                cost_usd=cost_usd
            )
        except asyncpg.UniqueViolationError:
            # Cache key already exists, ignore
            pass

    async def get_application_stats(self) -> Dict[str, int]:
        """
        Get application statistics for current user

        Returns:
            Dictionary with total, success, failed, skipped counts
        """
        total = await self.application_repo.count_by_user(
            self.context.tenant_id,
            self.context.user_id
        )
        success = await self.application_repo.count_by_user(
            self.context.tenant_id,
            self.context.user_id,
            status="success"
        )
        failed = await self.application_repo.count_by_user(
            self.context.tenant_id,
            self.context.user_id,
            status="failed"
        )
        skipped = await self.application_repo.count_by_user(
            self.context.tenant_id,
            self.context.user_id,
            status="skipped"
        )

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'skipped': skipped
        }
