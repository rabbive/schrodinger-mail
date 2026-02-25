"""Add P2P fields to contacts (peer_address, device_label).

Revision ID: 002_p2p_contacts
Revises: 001
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_p2p_contacts"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("peer_address", sa.String(length=255), nullable=True))
    op.add_column("contacts", sa.Column("device_label", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("contacts", "device_label")
    op.drop_column("contacts", "peer_address")

