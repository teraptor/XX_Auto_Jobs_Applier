"""create tenants table

Revision ID: 001
Revises:
Create Date: 2024-01-15 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы tenants"""
    op.execute("""
        CREATE TABLE tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) UNIQUE NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создание индекса для поиска по slug
    op.execute("""
        CREATE INDEX idx_tenants_slug ON tenants(slug)
    """)

    # Создание индекса для активных тенантов
    op.execute("""
        CREATE INDEX idx_tenants_status ON tenants(status)
    """)

    # Триггер для автоматического обновления updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)

    op.execute("""
        CREATE TRIGGER update_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Удаление таблицы tenants"""
    op.execute("DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP INDEX IF EXISTS idx_tenants_status")
    op.execute("DROP INDEX IF EXISTS idx_tenants_slug")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
