"""Add ASSESSMENT to ProjectStatus

Revision ID: f155fe9866a4
Revises: c9ef3732d9f7
Create Date: 2024-01-13 07:35:38.278792

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f155fe9866a4"
down_revision = "c9ef3732d9f7"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'ASSESSMENT' to the enum
    op.execute("COMMIT;")
    op.execute("ALTER TYPE projectstatus ADD VALUE 'pending assessment';")
    op.execute("BEGIN;")


def downgrade():
    pass
