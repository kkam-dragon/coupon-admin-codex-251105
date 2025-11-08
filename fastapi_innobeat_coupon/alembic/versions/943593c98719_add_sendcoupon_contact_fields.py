"""add_sendcoupon_contact_fields

Revision ID: 943593c98719
Revises: 06b7aa5a6788
Create Date: 2025-11-09 01:55:08.975448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '943593c98719'
down_revision: Union[str, None] = '06b7aa5a6788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column("client_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("sales_manager_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("requester_name_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("requester_phone_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("requester_phone_hash", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("requester_email_enc", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "requester_email_enc")
    op.drop_column("campaigns", "requester_phone_hash")
    op.drop_column("campaigns", "requester_phone_enc")
    op.drop_column("campaigns", "requester_name_enc")
    op.drop_column("campaigns", "sales_manager_name")
    op.drop_column("campaigns", "client_name")
