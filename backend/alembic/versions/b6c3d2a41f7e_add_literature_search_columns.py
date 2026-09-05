"""Add literature search columns

Revision ID: b6c3d2a41f7e
Revises: 0bd3b956b05e
Create Date: 2026-09-01 09:00:00.000000

Extends the initial schema with the fields needed by the week-2 literature
search feature:
  * search_sessions.expires_at      -> cache TTL
  * cached_papers.search_session_id -> link papers to their search session
  * cached_papers.summary           -> Vietnamese summary
  * cached_papers.relevance_score   -> relevance score
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c3d2a41f7e'
down_revision: Union[str, Sequence[str], None] = '0bd3b956b05e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the new columns to support cached literature search."""
    op.add_column(
        'search_sessions',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'cached_papers',
        sa.Column('search_session_id', sa.UUID(), nullable=True),
    )
    op.add_column(
        'cached_papers',
        sa.Column('summary', sa.Text(), nullable=True),
    )
    op.add_column(
        'cached_papers',
        sa.Column('relevance_score', sa.Float(), nullable=True),
    )
    op.create_foreign_key(
        'fk_cached_papers_search_session_id',
        'cached_papers',
        'search_sessions',
        ['search_session_id'],
        ['id'],
    )


def downgrade() -> None:
    """Rollback the added columns."""
    op.drop_constraint(
        'fk_cached_papers_search_session_id',
        'cached_papers',
        type_='foreignkey',
    )
    op.drop_column('cached_papers', 'relevance_score')
    op.drop_column('cached_papers', 'summary')
    op.drop_column('cached_papers', 'search_session_id')
    op.drop_column('search_sessions', 'expires_at')