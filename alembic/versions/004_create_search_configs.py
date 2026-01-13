"""create search_configs table

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 12:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы search_configs"""
    op.execute("""
        CREATE TABLE search_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            config JSONB NOT NULL,
            is_active BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_search_configs_tenant_user ON search_configs(tenant_id, user_id)
    """)

    op.execute("""
        CREATE INDEX idx_search_configs_active ON search_configs(tenant_id, user_id, is_active)
    """)

    # GIN индекс для JSONB поиска
    op.execute("""
        CREATE INDEX idx_search_configs_config_gin ON search_configs USING GIN (config)
    """)

    # Триггер для updated_at
    op.execute("""
        CREATE TRIGGER update_search_configs_updated_at
            BEFORE UPDATE ON search_configs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)

    # Комментарии
    op.execute("""
        COMMENT ON COLUMN search_configs.config IS 'JSONB с параметрами поиска из search_config.yaml'
    """)


def downgrade() -> None:
    """Удаление таблицы search_configs"""
    op.execute("DROP TRIGGER IF EXISTS update_search_configs_updated_at ON search_configs")
    op.execute("DROP INDEX IF EXISTS idx_search_configs_config_gin")
    op.execute("DROP INDEX IF EXISTS idx_search_configs_active")
    op.execute("DROP INDEX IF EXISTS idx_search_configs_tenant_user")
    op.execute("DROP TABLE IF EXISTS search_configs CASCADE")
