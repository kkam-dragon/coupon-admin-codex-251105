"""make_campaign_client_optional

Revision ID: fc82e281f51b
Revises: 943593c98719
Create Date: 2025-11-09 02:26:53.271883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc82e281f51b'
down_revision: Union[str, None] = '943593c98719'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "campaigns",
        "client_id",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "campaigns",
        "client_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
