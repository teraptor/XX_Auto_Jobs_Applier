"""create job_tasks table

Revision ID: 007
Revises: 006
Create Date: 2024-01-15 12:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы job_tasks"""
    op.execute("""
        CREATE TABLE job_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            task_id UUID UNIQUE NOT NULL,
            result_id UUID,
            task_type VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            payload JSONB,
            result JSONB,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_job_tasks_tenant_user ON job_tasks(tenant_id, user_id)
    """)

    op.execute("""
        CREATE INDEX idx_job_tasks_task_id ON job_tasks(task_id)
    """)

    op.execute("""
        CREATE INDEX idx_job_tasks_result_id ON job_tasks(result_id)
    """)

    op.execute("""
        CREATE INDEX idx_job_tasks_status ON job_tasks(tenant_id, status)
    """)

    op.execute("""
        CREATE INDEX idx_job_tasks_created_at ON job_tasks(created_at DESC)
    """)

    # Комментарии
    op.execute("""
        COMMENT ON COLUMN job_tasks.task_id IS 'UUID из Redis Queue - связь с FIFO очередью'
    """)

    op.execute("""
        COMMENT ON COLUMN job_tasks.result_id IS 'UUID результата из Redis - связь с results:completed/failed'
    """)

    op.execute("""
        COMMENT ON COLUMN job_tasks.status IS 'pending | processing | completed | failed'
    """)

    op.execute("""
        COMMENT ON TABLE job_tasks IS 'История всех задач для долговременного хранения (дополнение к Redis TTL 24h)'
    """)


def downgrade() -> None:
    """Удаление таблицы job_tasks"""
    op.execute("DROP INDEX IF EXISTS idx_job_tasks_created_at")
    op.execute("DROP INDEX IF EXISTS idx_job_tasks_status")
    op.execute("DROP INDEX IF EXISTS idx_job_tasks_result_id")
    op.execute("DROP INDEX IF EXISTS idx_job_tasks_task_id")
    op.execute("DROP INDEX IF EXISTS idx_job_tasks_tenant_user")
    op.execute("DROP TABLE IF EXISTS job_tasks CASCADE")
