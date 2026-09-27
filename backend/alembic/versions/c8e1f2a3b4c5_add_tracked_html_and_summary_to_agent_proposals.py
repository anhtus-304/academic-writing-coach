"""Add tracked_html and summary to agent_proposals

Revision ID: c8e1f2a3b4c5
Revises: a7f2e1b3c4d5
Create Date: 2026-09-27 18:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e1f2a3b4c5'
down_revision: Union[str, None] = 'a7f2e1b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_proposals', sa.Column('tracked_html', sa.Text(), nullable=True))
    op.add_column('agent_proposals', sa.Column('summary', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_proposals', 'summary')
    op.drop_column('agent_proposals', 'tracked_html')
