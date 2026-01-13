"""create browser_sessions table

Revision ID: 005
Revises: 004
Create Date: 2024-01-15 12:20:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы browser_sessions"""
    op.execute("""
        CREATE TABLE browser_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_state JSONB NOT NULL,
            is_valid BOOLEAN DEFAULT true,
            last_validated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_tenant_user_session UNIQUE(tenant_id, user_id)
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_browser_sessions_tenant_user ON browser_sessions(tenant_id, user_id)
    """)

    op.execute("""
        CREATE INDEX idx_browser_sessions_valid ON browser_sessions(is_valid)
    """)

    # Триггер для updated_at
    op.execute("""
        CREATE TRIGGER update_browser_sessions_updated_at
            BEFORE UPDATE ON browser_sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)

    # Комментарии
    op.execute("""
        COMMENT ON COLUMN browser_sessions.session_state IS 'Playwright session state (cookies, localStorage) в JSONB'
    """)


def downgrade() -> None:
    """Удаление таблицы browser_sessions"""
    op.execute("DROP TRIGGER IF EXISTS update_browser_sessions_updated_at ON browser_sessions")
    op.execute("DROP INDEX IF EXISTS idx_browser_sessions_valid")
    op.execute("DROP INDEX IF EXISTS idx_browser_sessions_tenant_user")
    op.execute("DROP TABLE IF EXISTS browser_sessions CASCADE")
