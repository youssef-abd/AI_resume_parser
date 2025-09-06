"""init schema

Revision ID: 3dda38bea92e
Revises: 4dbfa0cbe60f
Create Date: 2025-09-03 13:36:42.770514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '3dda38bea92e'
down_revision: Union[str, Sequence[str], None] = '4dbfa0cbe60f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create core tables for resumes and jobs."""
    # Ensure pgvector extension exists (should be created in 4dbfa0cbe60f, but safe to assert)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # resumes table
    op.create_table(
        'resumes',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('candidate_name', sa.String(length=255), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('cleaned_text', sa.Text(), nullable=False),
        sa.Column('skills', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description_cleaned', sa.Text(), nullable=False),
        sa.Column('required_skills', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Optional supporting indexes
    op.create_index('ix_jobs_title', 'jobs', ['title'], unique=False)
    op.create_index('ix_resumes_candidate_name', 'resumes', ['candidate_name'], unique=False)


def downgrade() -> None:
    """Drop core tables and indexes."""
    # Drop indexes first
    op.drop_index('ix_resumes_candidate_name', table_name='resumes')
    op.drop_index('ix_jobs_title', table_name='jobs')

    # Drop tables
    op.drop_table('jobs')
    op.drop_table('resumes')
