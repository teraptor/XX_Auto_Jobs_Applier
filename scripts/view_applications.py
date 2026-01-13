#!/usr/bin/env python3
"""
View Applications CLI Script
View job application history from PostgreSQL
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseManager
from src.repositories import ApplicationRepository, UserRepository


async def list_applications(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """List applications for a user"""
    app_repo = ApplicationRepository(db_manager.pool)

    try:
        applications = await app_repo.list_by_user(
            tenant_id,
            user_id,
            limit=limit,
            offset=offset,
            status=status
        )
        return applications
    except Exception as e:
        print(f"Error listing applications: {e}")
        sys.exit(1)


async def get_application_stats(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str
):
    """Get application statistics"""
    app_repo = ApplicationRepository(db_manager.pool)

    try:
        total = await app_repo.count_by_user(tenant_id, user_id)
        success = await app_repo.count_by_user(tenant_id, user_id, status="success")
        failed = await app_repo.count_by_user(tenant_id, user_id, status="failed")
        skipped = await app_repo.count_by_user(tenant_id, user_id, status="skipped")

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'skipped': skipped
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        sys.exit(1)


async def get_application_by_task(
    db_manager: DatabaseManager,
    tenant_id: str,
    task_id: str
):
    """Get application by task_id"""
    app_repo = ApplicationRepository(db_manager.pool)

    try:
        application = await app_repo.get_by_task_id(task_id, tenant_id)
        return application
    except Exception as e:
        print(f"Error getting application: {e}")
        sys.exit(1)


def format_application(app: dict) -> str:
    """Format application for display"""
    status_icons = {
        'success': '✅',
        'failed': '❌',
        'skipped': '⏭️',
        'pending': '⏳'
    }

    status_icon = status_icons.get(app['status'], '❓')

    lines = [
        f"{status_icon} {app['position_title']} at {app['company_name']}",
        f"   Vacancy ID: {app['vacancy_id']}",
    ]

    if app['vacancy_url']:
        lines.append(f"   URL: {app['vacancy_url']}")

    if app['task_id']:
        lines.append(f"   Task ID: {app['task_id']}")

    lines.append(f"   Status: {app['status']}")
    lines.append(f"   Applied: {app['applied_at']}")

    if app['error_message']:
        lines.append(f"   Error: {app['error_message']}")

    if app['cover_letter']:
        cover_preview = app['cover_letter'][:100] + "..." if len(app['cover_letter']) > 100 else app['cover_letter']
        lines.append(f"   Cover Letter: {cover_preview}")

    return "\n".join(lines)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
Usage:
    python scripts/view_applications.py list <tenant_id> <user_id> [--status success|failed|skipped] [--limit N]
    python scripts/view_applications.py stats <tenant_id> <user_id>
    python scripts/view_applications.py task <tenant_id> <task_id>

Examples:
    # List all applications
    python scripts/view_applications.py list <tenant_id> <user_id>

    # List only successful applications
    python scripts/view_applications.py list <tenant_id> <user_id> --status success

    # List with custom limit
    python scripts/view_applications.py list <tenant_id> <user_id> --limit 100

    # Show statistics
    python scripts/view_applications.py stats <tenant_id> <user_id>

    # Find application by task_id
    python scripts/view_applications.py task <tenant_id> <task_id>

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
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

        if command == "list":
            if len(sys.argv) < 4:
                print("Usage: view_applications.py list <tenant_id> <user_id> [--status status] [--limit N]")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            # Parse optional arguments
            status = None
            limit = 50

            i = 4
            while i < len(sys.argv):
                if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                    status = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                    limit = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1

            # Verify user exists
            user_repo = UserRepository(db_manager.pool)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if not user:
                print(f"ERROR: User not found: {user_id}")
                sys.exit(1)

            applications = await list_applications(
                db_manager,
                tenant_id,
                user_id,
                status=status,
                limit=limit
            )

            if not applications:
                filter_text = f" with status '{status}'" if status else ""
                print(f"No applications found{filter_text}")
            else:
                filter_text = f" ({status})" if status else ""
                print(f"\nFound {len(applications)} application(s){filter_text}:\n")

                for app in applications:
                    print(format_application(app))
                    print()

        elif command == "stats":
            if len(sys.argv) < 4:
                print("Usage: view_applications.py stats <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            # Verify user exists
            user_repo = UserRepository(db_manager.pool)
            user = await user_repo.get_by_id(user_id, tenant_id)
            if not user:
                print(f"ERROR: User not found: {user_id}")
                sys.exit(1)

            stats = await get_application_stats(db_manager, tenant_id, user_id)

            print(f"\nApplication Statistics for {user['email']}:\n")
            print(f"  Total Applications: {stats['total']}")
            print(f"  ✅ Success: {stats['success']}")
            print(f"  ❌ Failed: {stats['failed']}")
            print(f"  ⏭️  Skipped: {stats['skipped']}")

            if stats['total'] > 0:
                success_rate = (stats['success'] / stats['total']) * 100
                print(f"\n  Success Rate: {success_rate:.1f}%")

        elif command == "task":
            if len(sys.argv) < 4:
                print("Usage: view_applications.py task <tenant_id> <task_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            task_id = sys.argv[3]

            application = await get_application_by_task(db_manager, tenant_id, task_id)

            if not application:
                print(f"No application found for task_id: {task_id}")
            else:
                print("\nApplication found:\n")
                print(format_application(application))
                print()

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
