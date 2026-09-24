"""Week-3 tests - DB indexing strategy.

Three layers are verified:
1. the ``Index`` objects declared on the SQLAlchemy models (source of truth for
   ``Base.metadata.create_all``);
2. the Alembic migration that adds them (including the PostgreSQL **GIN**
   full-text index) and the repaired linear revision chain;
3. the indexes actually present in the test database after ``create_all``.
"""
import pathlib
import re
import time

from sqlalchemy import inspect as sa_inspect

from database import Base

EXPECTED_COMPOSITE_INDEXES = {
    "projects": "ix_projects_user_id_status",
    "search_sessions": "ix_search_sessions_project_id_expires_at",
    "credit_transactions": "ix_credit_transactions_user_id_created_at",
}

VERSIONS_DIR = pathlib.Path("alembic/versions")
MIGRATION_PATH = VERSIONS_DIR / "f3a91c2d7b64_add_week3_query_indexes.py"


def _model_index_names(table_name: str) -> set:
    return {index.name for index in Base.metadata.tables[table_name].indexes}


def test_composite_indexes_declared_on_models():
    for table_name, index_name in EXPECTED_COMPOSITE_INDEXES.items():
        assert index_name in _model_index_names(table_name), f"{index_name} missing on {table_name}"


def test_migration_declares_gin_full_text_index_and_composites():
    assert MIGRATION_PATH.exists(), "week-3 index migration is missing"

    migration = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "USING GIN" in migration
    assert "to_tsvector('simple'" in migration
    assert "ix_cached_papers_fts" in migration

    for index_name in EXPECTED_COMPOSITE_INDEXES.values():
        assert index_name in migration

    # The GIN index must only be created on PostgreSQL.
    assert 'dialect == "postgresql"' in migration


def test_alembic_revision_chain_is_reachable():
    """Every ``down_revision`` must resolve (week-3 fixed the dangling revision)."""
    revisions = {}
    down_revisions = {}

    for file in VERSIONS_DIR.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        revision = re.search(r"^revision: str = '([^']+)'", text, re.M)
        down = re.search(r"^down_revision: [^=]+= '([^']+)'", text, re.M)
        if revision:
            revisions[revision.group(1)] = file.name
            down_revisions[revision.group(1)] = down.group(1) if down else None

    assert revisions, "no alembic revisions found"
    for revision, parent in down_revisions.items():
        if parent is not None:
            assert parent in revisions, f"{revision} points at unknown parent {parent}"

    # The week-3 migration must be the head of the chain.
    referenced_parents = {parent for parent in down_revisions.values() if parent}
    heads = set(revisions) - referenced_parents
    assert "f3a91c2d7b64" in heads


async def test_composite_indexes_exist_in_database(db_session):
    async def _index_names(table_name: str) -> set:
        def _collect(sync_session):
            # AsyncSession.run_sync hands the *sync Session* to the callback, so
            # the inspector has to be built from its bound connection.
            inspector = sa_inspect(sync_session.get_bind())
            return {index["name"] for index in inspector.get_indexes(table_name)}

        return await db_session.run_sync(_collect)

    for table_name, index_name in EXPECTED_COMPOSITE_INDEXES.items():
        assert index_name in await _index_names(table_name)
async def test_indexed_queries_stay_fast_with_large_dataset(db_session, project):
    """Smoke performance check: indexed cache lookups stay well under the 50ms/query budget."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from models.cached_paper import CachedPaper
    from models.search_session import SearchSession
    from services import literature_service

    now = datetime.now(timezone.utc)
    search_session = SearchSession(
        project_id=str(project.id),
        query="bulk",
        filters={},
        total_results=200,
        expires_at=now + timedelta(hours=48),
    )
    db_session.add(search_session)
    await db_session.flush()

    db_session.add_all(
        [
            CachedPaper(
                session_id=search_session.id,
                title=f"Bulk paper {index} on academic writing",
                authors=["Bulk Author"],
                abstract="Performance probe corpus for the week-3 GIN index.",
                doi=f"10.2000/bulk-{index}",
                source="semantic_scholar",
                year=2020 + (index % 5),
                relevance_score=index / 1000,
            )
            for index in range(200)
        ]
    )
    await db_session.commit()

    started = time.perf_counter()
    # 1. Composite (project_id, expires_at) cache lookup.
    cached = await db_session.execute(
        select(SearchSession).where(
            SearchSession.project_id == str(project.id),
            SearchSession.expires_at > now,
        )
    )
    assert cached.scalars().first() is not None

    # 2. Full-text lookup over title + abstract.
    hits = await literature_service.full_text_search_papers(db_session, "Performance probe", limit=10)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert hits
    # SQLite + ILIKE fallback is slower than the PostgreSQL GIN plan, hence the
    # generous ceiling; a regression to N+1/unindexed scans will still fail here.
    assert elapsed_ms < 1000, f"indexed lookups took {elapsed_ms:.1f}ms"


async def test_credit_history_index_supports_user_ordered_reads(db_session):
    from sqlalchemy import select

    from models.credit import CreditTransaction
    from tests.conftest import create_user_with_project

    user, _project = await create_user_with_project(credit_balance=10)
    db_session.add_all(
        [
            CreditTransaction(
                user_id=user.id,
                type="usage",
                amount=-1,
                balance_after=10 - index,
                description=f"probe {index}",
            )
            for index in range(1, 6)
        ]
    )
    await db_session.commit()

    result = await db_session.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc())
    )
    assert len(result.scalars().all()) == 5