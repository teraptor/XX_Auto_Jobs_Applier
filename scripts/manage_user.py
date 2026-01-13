#!/usr/bin/env python3
"""
User Management CLI Script
Create and manage users with HH.ru credentials
"""
import asyncio
import sys
import os
from pathlib import Path
from cryptography.fernet import Fernet
import base64

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseManager
from src.repositories import UserRepository, TenantRepository


def get_encryption_key() -> bytes:
    """Get encryption key from environment"""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        print("ERROR: ENCRYPTION_KEY environment variable not set")
        print("Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        sys.exit(1)
    return key.encode()


def encrypt_password(password: str) -> str:
    """Encrypt password using Fernet"""
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(password.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt password using Fernet"""
    fernet = Fernet(get_encryption_key())
    encrypted_bytes = base64.b64decode(encrypted_password.encode())
    decrypted = fernet.decrypt(encrypted_bytes)
    return decrypted.decode()


async def create_user(
    db_manager: DatabaseManager,
    tenant_id: str,
    email: str,
    hh_login: str,
    hh_password: str
) -> dict:
    """Create a new user"""
    user_repo = UserRepository(db_manager.pool)

    try:
        # Encrypt password
        encrypted_password = encrypt_password(hh_password)

        user = await user_repo.create(
            tenant_id=tenant_id,
            email=email,
            hh_login=hh_login,
            hh_password_encrypted=encrypted_password,
            is_active=True
        )
        return user
    except Exception as e:
        print(f"Error creating user: {e}")
        sys.exit(1)


async def list_users(
    db_manager: DatabaseManager,
    tenant_id: str,
    is_active: bool = None
):
    """List users for a tenant"""
    user_repo = UserRepository(db_manager.pool)

    try:
        users = await user_repo.list_by_tenant(tenant_id, is_active=is_active, limit=100)
        return users
    except Exception as e:
        print(f"Error listing users: {e}")
        sys.exit(1)


async def get_user(db_manager: DatabaseManager, tenant_id: str, user_id: str) -> dict:
    """Get user by ID"""
    user_repo = UserRepository(db_manager.pool)

    try:
        user = await user_repo.get_by_id(user_id, tenant_id)
        if not user:
            print(f"User not found: {user_id}")
            sys.exit(1)
        return user
    except Exception as e:
        print(f"Error getting user: {e}")
        sys.exit(1)


async def update_user_status(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str,
    is_active: bool
):
    """Update user active status"""
    user_repo = UserRepository(db_manager.pool)

    try:
        user = await user_repo.update_active_status(user_id, tenant_id, is_active)
        if not user:
            print(f"User not found: {user_id}")
            sys.exit(1)
        return user
    except Exception as e:
        print(f"Error updating user: {e}")
        sys.exit(1)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
Usage:
    python scripts/manage_user.py create <tenant_id> <email> <hh_login> <hh_password>
    python scripts/manage_user.py list <tenant_id> [--active|--inactive]
    python scripts/manage_user.py get <tenant_id> <user_id>
    python scripts/manage_user.py deactivate <tenant_id> <user_id>
    python scripts/manage_user.py activate <tenant_id> <user_id>

Examples:
    python scripts/manage_user.py create <tenant_id> "user@example.com" "hh_login" "hh_password"
    python scripts/manage_user.py list <tenant_id>
    python scripts/manage_user.py list <tenant_id> --active
    python scripts/manage_user.py get <tenant_id> <user_id>
    python scripts/manage_user.py deactivate <tenant_id> <user_id>

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
    ENCRYPTION_KEY: Fernet encryption key for passwords
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
            if len(sys.argv) < 6:
                print("Usage: manage_user.py create <tenant_id> <email> <hh_login> <hh_password>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            email = sys.argv[3]
            hh_login = sys.argv[4]
            hh_password = sys.argv[5]

            # Verify tenant exists
            tenant_repo = TenantRepository(db_manager.pool)
            tenant = await tenant_repo.get_by_id(tenant_id)
            if not tenant:
                print(f"ERROR: Tenant not found: {tenant_id}")
                sys.exit(1)

            user = await create_user(db_manager, tenant_id, email, hh_login, hh_password)

            print(f"✅ User created successfully!")
            print(f"   ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   HH Login: {user['hh_login']}")
            print(f"   Active: {user['is_active']}")

        elif command == "list":
            if len(sys.argv) < 3:
                print("Usage: manage_user.py list <tenant_id> [--active|--inactive]")
                sys.exit(1)

            tenant_id = sys.argv[2]
            is_active = None

            if len(sys.argv) > 3:
                if sys.argv[3] == "--active":
                    is_active = True
                elif sys.argv[3] == "--inactive":
                    is_active = False

            users = await list_users(db_manager, tenant_id, is_active)

            if not users:
                print("No users found")
            else:
                print(f"\nFound {len(users)} user(s):\n")
                for user in users:
                    status = "✓ Active" if user['is_active'] else "✗ Inactive"
                    print(f"  • {user['email']} [{status}]")
                    print(f"    ID: {user['id']}")
                    print(f"    HH Login: {user['hh_login']}")
                    print(f"    Created: {user['created_at']}")
                    print()

        elif command == "get":
            if len(sys.argv) < 4:
                print("Usage: manage_user.py get <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            user = await get_user(db_manager, tenant_id, user_id)

            print(f"\nUser Details:")
            print(f"  ID: {user['id']}")
            print(f"  Email: {user['email']}")
            print(f"  HH Login: {user['hh_login']}")
            print(f"  Active: {user['is_active']}")
            print(f"  Created: {user['created_at']}")
            print(f"  Updated: {user['updated_at']}")

        elif command == "deactivate":
            if len(sys.argv) < 4:
                print("Usage: manage_user.py deactivate <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            user = await update_user_status(db_manager, tenant_id, user_id, False)

            print(f"✅ User deactivated: {user['email']}")

        elif command == "activate":
            if len(sys.argv) < 4:
                print("Usage: manage_user.py activate <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            user = await update_user_status(db_manager, tenant_id, user_id, True)

            print(f"✅ User activated: {user['email']}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
