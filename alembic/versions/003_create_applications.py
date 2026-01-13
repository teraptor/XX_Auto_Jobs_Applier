"""create applications table

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 12:10:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы applications"""
    op.execute("""
        CREATE TABLE applications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            task_id UUID,
            vacancy_id VARCHAR(255) NOT NULL,
            vacancy_url TEXT,
            company_name VARCHAR(500),
            position_title VARCHAR(500),
            status VARCHAR(50) NOT NULL,
            cover_letter TEXT,
            error_message TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_tenant_user_vacancy UNIQUE(tenant_id, user_id, vacancy_id)
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_applications_tenant_user ON applications(tenant_id, user_id)
    """)

    op.execute("""
        CREATE INDEX idx_applications_status ON applications(status)
    """)

    op.execute("""
        CREATE INDEX idx_applications_task_id ON applications(task_id)
    """)

    op.execute("""
        CREATE INDEX idx_applications_applied_at ON applications(applied_at DESC)
    """)

    # Комментарии
    op.execute("""
        COMMENT ON COLUMN applications.task_id IS 'UUID задачи из Redis Queue для tracking'
    """)

    op.execute("""
        COMMENT ON COLUMN applications.status IS 'success | failed | skipped'
    """)


def downgrade() -> None:
    """Удаление таблицы applications"""
    op.execute("DROP INDEX IF EXISTS idx_applications_applied_at")
    op.execute("DROP INDEX IF EXISTS idx_applications_task_id")
    op.execute("DROP INDEX IF EXISTS idx_applications_status")
    op.execute("DROP INDEX IF EXISTS idx_applications_tenant_user")
    op.execute("DROP TABLE IF EXISTS applications CASCADE")
