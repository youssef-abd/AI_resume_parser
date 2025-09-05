"""merge heads

Revision ID: 8bb148026c52
Revises: 3dda38bea92e, c9a1f86c3b1b
Create Date: 2025-09-03 19:21:58.534100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bb148026c52'
down_revision: Union[str, Sequence[str], None] = ('3dda38bea92e', 'c9a1f86c3b1b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
