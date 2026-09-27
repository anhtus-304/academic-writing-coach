"""Add agent workflow tables

Revision ID: a7f2e1b3c4d5
Revises: b6c3d2a41f7e
Create Date: 2026-09-23 22:30:00.000000

Adds 5 new tables for the multi-agent workspace feature:
  * agent_jobs          — central job tracking
  * agent_job_stages    — individual stage execution records
  * agent_proposals     — diff-based proposals for human review
  * agent_decisions     — user accept/reject decisions on operations
  * document_versions   — immutable document snapshots for versioning
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f2e1b3c4d5'
down_revision: Union[str, None] = 'b6c3d2a41f7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agent_jobs ────────────────────────────────────────────────────
    op.create_table(
        'agent_jobs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('prompt_summary', sa.String(500), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('plan', sa.JSON(), nullable=True),
        sa.Column('context_snapshot', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(), nullable=True, unique=True, index=True),
        sa.Column('estimated_credits', sa.Integer(), server_default='0'),
        sa.Column('actual_credits', sa.Integer(), server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── agent_job_stages ──────────────────────────────────────────────
    op.create_table(
        'agent_job_stages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('agent_jobs.id'), nullable=False, index=True),
        sa.Column('stage_type', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('input_ref', sa.JSON(), nullable=True),
        sa.Column('output_ref', sa.JSON(), nullable=True),
        sa.Column('depends_on', sa.JSON(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('max_retries', sa.Integer(), server_default='2'),
        sa.Column('tokens_used', sa.Integer(), server_default='0'),
        sa.Column('credits_charged', sa.Integer(), server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── agent_proposals ───────────────────────────────────────────────
    op.create_table(
        'agent_proposals',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('job_id', sa.String(), sa.ForeignKey('agent_jobs.id'), nullable=False, index=True),
        sa.Column('base_version', sa.Integer(), nullable=False),
        sa.Column('base_hash', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_section_id', sa.String(), nullable=True),
        sa.Column('operations', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ── agent_decisions ───────────────────────────────────────────────
    op.create_table(
        'agent_decisions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('proposal_id', sa.String(), sa.ForeignKey('agent_proposals.id'), nullable=False, index=True),
        sa.Column('operation_id', sa.String(), nullable=True),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('actor_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── document_versions ─────────────────────────────────────────────
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('word_count', sa.Integer(), server_default='0'),
        sa.Column('source_job_id', sa.String(), sa.ForeignKey('agent_jobs.id'), nullable=True),
        sa.Column('source_proposal_id', sa.String(), sa.ForeignKey('agent_proposals.id'), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('document_versions')
    op.drop_table('agent_decisions')
    op.drop_table('agent_proposals')
    op.drop_table('agent_job_stages')
    op.drop_table('agent_jobs')
