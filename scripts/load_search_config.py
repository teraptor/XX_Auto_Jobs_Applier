#!/usr/bin/env python3
"""
Search Config Loading CLI Script
Load search configuration from YAML file to PostgreSQL
"""
import asyncio
import sys
import os
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseManager
from src.repositories import SearchConfigRepository, UserRepository


async def load_config(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str,
    config_path: str,
    name: str,
    set_active: bool = True
) -> dict:
    """Load search config from YAML file"""
    config_repo = SearchConfigRepository(db_manager.pool)

    try:
        # Read YAML file
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            print(f"ERROR: Config file is empty: {config_path}")
            sys.exit(1)

        # Verify user exists
        user_repo = UserRepository(db_manager.pool)
        user = await user_repo.get_by_id(user_id, tenant_id)
        if not user:
            print(f"ERROR: User not found: {user_id}")
            sys.exit(1)

        # Create config
        search_config = await config_repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            config=config_data,
            is_active=False  # Will be set active below if requested
        )

        # Set as active if requested
        if set_active:
            search_config = await config_repo.set_active(
                search_config['id'],
                tenant_id,
                user_id
            )

        return search_config

    except FileNotFoundError:
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


async def list_configs(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str
):
    """List all search configs for a user"""
    config_repo = SearchConfigRepository(db_manager.pool)

    try:
        configs = await config_repo.list_by_user(tenant_id, user_id, limit=100)
        return configs
    except Exception as e:
        print(f"Error listing configs: {e}")
        sys.exit(1)


async def get_active_config(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str
):
    """Get active search config for a user"""
    config_repo = SearchConfigRepository(db_manager.pool)

    try:
        config = await config_repo.get_active(tenant_id, user_id)
        return config
    except Exception as e:
        print(f"Error getting active config: {e}")
        sys.exit(1)


async def set_active_config(
    db_manager: DatabaseManager,
    tenant_id: str,
    user_id: str,
    config_id: str
):
    """Set a config as active"""
    config_repo = SearchConfigRepository(db_manager.pool)

    try:
        config = await config_repo.set_active(config_id, tenant_id, user_id)
        if not config:
            print(f"ERROR: Config not found: {config_id}")
            sys.exit(1)
        return config
    except Exception as e:
        print(f"Error setting active config: {e}")
        sys.exit(1)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
Usage:
    python scripts/load_search_config.py load <tenant_id> <user_id> <config_path> <name> [--no-activate]
    python scripts/load_search_config.py list <tenant_id> <user_id>
    python scripts/load_search_config.py active <tenant_id> <user_id>
    python scripts/load_search_config.py set-active <tenant_id> <user_id> <config_id>

Examples:
    # Load config and set as active
    python scripts/load_search_config.py load <tenant_id> <user_id> data_folder/search_config.yaml "Python Developer"

    # Load config without activating
    python scripts/load_search_config.py load <tenant_id> <user_id> data_folder/search_config.yaml "Backup Config" --no-activate

    # List all configs
    python scripts/load_search_config.py list <tenant_id> <user_id>

    # Show active config
    python scripts/load_search_config.py active <tenant_id> <user_id>

    # Set a config as active
    python scripts/load_search_config.py set-active <tenant_id> <user_id> <config_id>

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

        if command == "load":
            if len(sys.argv) < 6:
                print("Usage: load_search_config.py load <tenant_id> <user_id> <config_path> <name> [--no-activate]")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]
            config_path = sys.argv[4]
            name = sys.argv[5]
            set_active = "--no-activate" not in sys.argv

            config = await load_config(
                db_manager,
                tenant_id,
                user_id,
                config_path,
                name,
                set_active
            )

            print(f"✅ Search config loaded successfully!")
            print(f"   ID: {config['id']}")
            print(f"   Name: {config['name']}")
            print(f"   Active: {config['is_active']}")
            print(f"   Created: {config['created_at']}")

        elif command == "list":
            if len(sys.argv) < 4:
                print("Usage: load_search_config.py list <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            configs = await list_configs(db_manager, tenant_id, user_id)

            if not configs:
                print("No search configs found")
            else:
                print(f"\nFound {len(configs)} config(s):\n")
                for config in configs:
                    active_marker = "⭐" if config['is_active'] else "  "
                    print(f"{active_marker} {config['name']}")
                    print(f"   ID: {config['id']}")
                    print(f"   Created: {config['created_at']}")

                    # Show brief config summary
                    config_data = config['config']
                    if isinstance(config_data, dict):
                        if 'position' in config_data:
                            print(f"   Position: {config_data['position']}")
                        if 'locations' in config_data:
                            print(f"   Locations: {config_data['locations']}")
                    print()

        elif command == "active":
            if len(sys.argv) < 4:
                print("Usage: load_search_config.py active <tenant_id> <user_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]

            config = await get_active_config(db_manager, tenant_id, user_id)

            if not config:
                print("No active search config found")
            else:
                print(f"\n⭐ Active Config: {config['name']}")
                print(f"   ID: {config['id']}")
                print(f"   Created: {config['created_at']}")
                print(f"\n   Configuration:")

                # Pretty print config
                config_data = config['config']
                if isinstance(config_data, dict):
                    for key, value in config_data.items():
                        print(f"      {key}: {value}")

        elif command == "set-active":
            if len(sys.argv) < 5:
                print("Usage: load_search_config.py set-active <tenant_id> <user_id> <config_id>")
                sys.exit(1)

            tenant_id = sys.argv[2]
            user_id = sys.argv[3]
            config_id = sys.argv[4]

            config = await set_active_config(db_manager, tenant_id, user_id, config_id)

            print(f"✅ Config set as active: {config['name']}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
