"""Week 3 - full-text + composite query indexes

Revision ID: f3a91c2d7b64
Revises: b6c3d2a41f7e
Create Date: 2026-09-17 09:00:00.000000

Performance hardening for the week-3 workloads:

* ``ix_cached_papers_fts`` - **GIN** full-text index over
  ``to_tsvector('simple', title || ' ' || abstract)`` on PostgreSQL so that
  literature re-use/full-text lookups stop doing sequential scans once the
  cache grows. The ``simple`` configuration is used on purpose: the corpus mixes
  Vietnamese and English, and stemming/stop-words of ``english`` would mangle
  Vietnamese tokens.
* ``ix_projects_user_id_status`` - dashboard always lists
  ``WHERE user_id = ? [AND status = ?]``.
* ``ix_search_sessions_project_id_expires_at`` - the 48h cache lookup filters
  ``project_id`` + ``expires_at``.
* ``ix_credit_transactions_user_id_created_at`` - credit history is paginated by
  ``user_id`` ordered by ``created_at DESC``.

All statements are guarded with ``IF NOT EXISTS`` (and the GIN index is only
emitted for PostgreSQL) so the migration is safe to re-run on databases that
already received the indexes through ``Base.metadata.create_all``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a91c2d7b64'
down_revision: Union[str, Sequence[str], None] = 'b6c3d2a41f7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FULLTEXT_INDEX_NAME = "ix_cached_papers_fts"
FULLTEXT_EXPRESSION = (
    "to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(abstract, ''))"
)

COMPOSITE_INDEXES = (
    ("ix_projects_user_id_status", "projects", ["user_id", "status"]),
    (
        "ix_search_sessions_project_id_expires_at",
        "search_sessions",
        ["project_id", "expires_at"],
    ),
    (
        "ix_credit_transactions_user_id_created_at",
        "credit_transactions",
        ["user_id", "created_at"],
    ),
)


def upgrade() -> None:
    """Create the GIN full-text index (PostgreSQL) and the composite indexes."""
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                f"CREATE INDEX IF NOT EXISTS {FULLTEXT_INDEX_NAME} "
                f"ON cached_papers USING GIN ({FULLTEXT_EXPRESSION})"
            )
        )
        # Refresh planner statistics right after building the new index.
        op.execute(sa.text("ANALYZE cached_papers"))

    for index_name, table_name, columns in COMPOSITE_INDEXES:
        op.create_index(index_name, table_name, columns, unique=False, if_not_exists=True)


def downgrade() -> None:
    """Drop the indexes created by this migration."""
    for index_name, table_name, _columns in reversed(COMPOSITE_INDEXES):
        op.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))

    if op.get_context().dialect.name == "postgresql":
        op.execute(sa.text(f"DROP INDEX IF EXISTS {FULLTEXT_INDEX_NAME}"))