"""add IVFFlat index for resumes.embedding

Revision ID: c9a1f86c3b1b
Revises: 4dbfa0cbe60f
Create Date: 2025-09-02 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c9a1f86c3b1b'
down_revision = '4dbfa0cbe60f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists in earlier migration.
    # Create IVFFlat index for cosine ANN search. Tune lists per data size (e.g., 100-200 for ~10k rows).
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS resumes_embedding_ivfflat
        ON resumes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
    )
    # Update planner stats for improved query planning
    op.execute("ANALYZE resumes;")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS resumes_embedding_ivfflat;")
