"""create llm_cache table

Revision ID: 006
Revises: 005
Create Date: 2024-01-15 12:25:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы llm_cache"""
    op.execute("""
        CREATE TABLE llm_cache (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            cache_key VARCHAR(255) NOT NULL,
            prompt_hash VARCHAR(64) NOT NULL,
            response_data JSONB NOT NULL,
            model_name VARCHAR(100),
            tokens_used INTEGER,
            cost_usd DECIMAL(10, 6),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_tenant_cache_key UNIQUE(tenant_id, cache_key)
        )
    """)

    # Индексы
    op.execute("""
        CREATE INDEX idx_llm_cache_tenant ON llm_cache(tenant_id)
    """)

    op.execute("""
        CREATE INDEX idx_llm_cache_prompt_hash ON llm_cache(prompt_hash)
    """)

    op.execute("""
        CREATE INDEX idx_llm_cache_created_at ON llm_cache(created_at DESC)
    """)

    # Комментарии
    op.execute("""
        COMMENT ON COLUMN llm_cache.cache_key IS 'Уникальный ключ для кэша (вопрос + контекст)'
    """)

    op.execute("""
        COMMENT ON COLUMN llm_cache.prompt_hash IS 'SHA256 хэш промпта для быстрого поиска дубликатов'
    """)


def downgrade() -> None:
    """Удаление таблицы llm_cache"""
    op.execute("DROP INDEX IF EXISTS idx_llm_cache_created_at")
    op.execute("DROP INDEX IF EXISTS idx_llm_cache_prompt_hash")
    op.execute("DROP INDEX IF EXISTS idx_llm_cache_tenant")
    op.execute("DROP TABLE IF EXISTS llm_cache CASCADE")
