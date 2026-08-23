"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
<<<<<<< HEAD
down_revision: Union[str, None] = ${repr(down_revision)}
=======
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
<<<<<<< HEAD
=======
    """Upgrade schema."""
>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
<<<<<<< HEAD
=======
    """Downgrade schema."""
>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027
    ${downgrades if downgrades else "pass"}
