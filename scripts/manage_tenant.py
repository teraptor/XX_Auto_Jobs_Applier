#!/usr/bin/env python3
"""
Tenant Management CLI Script
Create and manage tenants for multi-tenant system
"""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseManager
from src.repositories import TenantRepository


async def create_tenant(db_manager: DatabaseManager, name: str, slug: str) -> dict:
    """Create a new tenant"""
    tenant_repo = TenantRepository(db_manager.pool)

    try:
        tenant = await tenant_repo.create(name=name, slug=slug, status="active")
        return tenant
    except Exception as e:
        print(f"Error creating tenant: {e}")
        sys.exit(1)


async def list_tenants(db_manager: DatabaseManager, status: str = None):
    """List all tenants"""
    tenant_repo = TenantRepository(db_manager.pool)

    try:
        tenants = await tenant_repo.list_all(status=status, limit=100)
        return tenants
    except Exception as e:
        print(f"Error listing tenants: {e}")
        sys.exit(1)


async def get_tenant(db_manager: DatabaseManager, identifier: str) -> dict:
    """Get tenant by ID or slug"""
    tenant_repo = TenantRepository(db_manager.pool)

    try:
        # Try as UUID first
        if len(identifier) == 36 and '-' in identifier:
            tenant = await tenant_repo.get_by_id(identifier)
        else:
            tenant = await tenant_repo.get_by_slug(identifier)

        if not tenant:
            print(f"Tenant not found: {identifier}")
            sys.exit(1)

        return tenant
    except Exception as e:
        print(f"Error getting tenant: {e}")
        sys.exit(1)


async def update_tenant_status(db_manager: DatabaseManager, tenant_id: str, status: str):
    """Update tenant status"""
    tenant_repo = TenantRepository(db_manager.pool)

    try:
        tenant = await tenant_repo.update_status(tenant_id, status)
        if not tenant:
            print(f"Tenant not found: {tenant_id}")
            sys.exit(1)
        return tenant
    except Exception as e:
        print(f"Error updating tenant: {e}")
        sys.exit(1)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
Usage:
    python scripts/manage_tenant.py create <name> <slug>
    python scripts/manage_tenant.py list [--status active|suspended]
    python scripts/manage_tenant.py get <tenant_id_or_slug>
    python scripts/manage_tenant.py suspend <tenant_id>
    python scripts/manage_tenant.py activate <tenant_id>

Examples:
    python scripts/manage_tenant.py create "Company A" company-a
    python scripts/manage_tenant.py list
    python scripts/manage_tenant.py list --status active
    python scripts/manage_tenant.py get company-a
    python scripts/manage_tenant.py suspend <tenant_id>
        """)
        sys.exit(1)

    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Example: export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'")
        sys.exit(1)

    # Initialize database
    db_manager = DatabaseManager(database_url)
    await db_manager.connect()

    try:
        command = sys.argv[1]

        if command == "create":
            if len(sys.argv) < 4:
                print("Usage: manage_tenant.py create <name> <slug>")
                sys.exit(1)

            name = sys.argv[2]
            slug = sys.argv[3]

            tenant = await create_tenant(db_manager, name, slug)

            print(f"✅ Tenant created successfully!")
            print(f"   ID: {tenant['id']}")
            print(f"   Name: {tenant['name']}")
            print(f"   Slug: {tenant['slug']}")
            print(f"   Status: {tenant['status']}")

        elif command == "list":
            status = None
            if len(sys.argv) > 2 and sys.argv[2] == "--status":
                status = sys.argv[3] if len(sys.argv) > 3 else None

            tenants = await list_tenants(db_manager, status)

            if not tenants:
                print("No tenants found")
            else:
                print(f"\nFound {len(tenants)} tenant(s):\n")
                for tenant in tenants:
                    print(f"  • {tenant['name']} ({tenant['slug']})")
                    print(f"    ID: {tenant['id']}")
                    print(f"    Status: {tenant['status']}")
                    print(f"    Created: {tenant['created_at']}")
                    print()

        elif command == "get":
            if len(sys.argv) < 3:
                print("Usage: manage_tenant.py get <tenant_id_or_slug>")
                sys.exit(1)

            identifier = sys.argv[2]
            tenant = await get_tenant(db_manager, identifier)

            print(f"\nTenant Details:")
            print(f"  ID: {tenant['id']}")
            print(f"  Name: {tenant['name']}")
            print(f"  Slug: {tenant['slug']}")
            print(f"  Status: {tenant['status']}")
            print(f"  Created: {tenant['created_at']}")
            print(f"  Updated: {tenant['updated_at']}")

        elif command == "suspend":
            if len(sys.argv) < 3:
                print("Usage: manage_tenant.py suspend <tenant_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            tenant = await update_tenant_status(db_manager, tenant_id, "suspended")

            print(f"✅ Tenant suspended: {tenant['name']}")

        elif command == "activate":
            if len(sys.argv) < 3:
                print("Usage: manage_tenant.py activate <tenant_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            tenant = await update_tenant_status(db_manager, tenant_id, "active")

            print(f"✅ Tenant activated: {tenant['name']}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
