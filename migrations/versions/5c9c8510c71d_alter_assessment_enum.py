"""Alter assessment enum

Revision ID: 5c9c8510c71d
Revises: f155fe9866a4
Create Date: 2024-01-13 07:43:30.201822

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c9c8510c71d"
down_revision = "f155fe9866a4"
branch_labels = None
depends_on = None


def upgrade():

    # Add 'ASSESSMENT' to the enum
    op.execute("COMMIT;")
    op.execute("ALTER TYPE projectstatus ADD VALUE 'ASSESSMENT';")
    op.execute("BEGIN;")


def downgrade():
    pass


def downgrade():
    pass
