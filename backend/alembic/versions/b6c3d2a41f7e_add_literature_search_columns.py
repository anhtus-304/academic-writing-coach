"""Add literature search columns

Revision ID: b6c3d2a41f7e
Revises: 146032681bd8
Create Date: 2026-09-01 09:00:00.000000

Extends the initial schema with the fields needed by the week-2 literature
search feature:
  * search_sessions.expires_at      -> cache TTL
  * cached_papers.search_session_id -> link papers to their search session
  * cached_papers.summary           -> Vietnamese summary
  * cached_papers.relevance_score   -> relevance score

NOTE (week 3 fix): this revision previously pointed at a non-existent parent
revision ``0bd3b956b05e``, which made ``alembic upgrade head`` fail with
"Can't locate revision identified by '0bd3b956b05e'". Revision
``146032681bd8`` (add literature and draft tables) already creates all four
columns, therefore this migration is now re-parented after it and became
**idempotent**: columns/constraints are only created when missing so it is safe
on both fresh and already-migrated databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c3d2a41f7e'
down_revision: Union[str, Sequence[str], None] = '146032681bd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set:
    """Return the current column names of ``table`` (empty set when unknown)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _existing_fk_names(table: str) -> set:
    """Return foreign-key constraint names already defined on ``table``."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {fk.get("name") for fk in inspector.get_foreign_keys(table)}


def upgrade() -> None:
    """Add the new columns to support cached literature search (idempotent)."""
    search_session_columns = _existing_columns('search_sessions')
    cached_paper_columns = _existing_columns('cached_papers')

    if 'expires_at' not in search_session_columns:
        op.add_column(
            'search_sessions',
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        )
    if 'search_session_id' not in cached_paper_columns:
        op.add_column(
            'cached_papers',
            sa.Column('search_session_id', sa.String(), nullable=True),
        )
    if 'summary' not in cached_paper_columns:
        op.add_column(
            'cached_papers',
            sa.Column('summary', sa.Text(), nullable=True),
        )
    if 'relevance_score' not in cached_paper_columns:
        op.add_column(
            'cached_papers',
            sa.Column('relevance_score', sa.Float(), nullable=True),
        )

    if 'fk_cached_papers_search_session_id' not in _existing_fk_names('cached_papers'):
        op.create_foreign_key(
            'fk_cached_papers_search_session_id',
            'cached_papers',
            'search_sessions',
            ['search_session_id'],
            ['id'],
        )


def downgrade() -> None:
    """Rollback the added columns (only when this migration created them)."""
    if 'fk_cached_papers_search_session_id' in _existing_fk_names('cached_papers'):
        op.drop_constraint(
            'fk_cached_papers_search_session_id',
            'cached_papers',
            type_='foreignkey',
        )

    cached_paper_columns = _existing_columns('cached_papers')
    if 'relevance_score' in cached_paper_columns:
        op.drop_column('cached_papers', 'relevance_score')
    if 'summary' in cached_paper_columns:
        op.drop_column('cached_papers', 'summary')
    if 'search_session_id' in cached_paper_columns:
        op.drop_column('cached_papers', 'search_session_id')

    if 'expires_at' in _existing_columns('search_sessions'):
        op.drop_column('search_sessions', 'expires_at')