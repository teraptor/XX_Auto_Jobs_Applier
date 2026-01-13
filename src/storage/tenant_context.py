"""
Tenant Context
Provides tenant isolation context for multi-tenant operations
"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class TenantContext:
    """
    Tenant context for dependency injection
    Used to provide tenant_id and user_id throughout the application
    """
    tenant_id: str
    user_id: str

    def __str__(self) -> str:
        return f"TenantContext(tenant={self.tenant_id[:8]}..., user={self.user_id[:8]}...)"

    def __repr__(self) -> str:
        return self.__str__()


# Thread-local storage for tenant context (for sync code)
_current_context: Optional[TenantContext] = None


def get_current_context() -> Optional[TenantContext]:
    """Get current tenant context"""
    return _current_context


def set_current_context(context: TenantContext) -> None:
    """Set current tenant context"""
    global _current_context
    _current_context = context


def clear_current_context() -> None:
    """Clear current tenant context"""
    global _current_context
    _current_context = None
