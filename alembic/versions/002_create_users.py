"""create users table

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 12:05:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы users"""
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            hh_login VARCHAR(255),
            hh_password_encrypted TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_tenant_email UNIQUE(tenant_id, email)
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_users_tenant ON users(tenant_id)
    """)

    op.execute("""
        CREATE INDEX idx_users_email ON users(email)
    """)

    op.execute("""
        CREATE INDEX idx_users_active ON users(is_active)
    """)

    # Триггер для updated_at
    op.execute("""
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Удаление таблицы users"""
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users")
    op.execute("DROP INDEX IF EXISTS idx_users_active")
    op.execute("DROP INDEX IF EXISTS idx_users_email")
    op.execute("DROP INDEX IF EXISTS idx_users_tenant")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
