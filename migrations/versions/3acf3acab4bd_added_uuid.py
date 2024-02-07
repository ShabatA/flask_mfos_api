"""added uuid

Revision ID: 3acf3acab4bd
Revises: 5d5e9f9ee3c7
Create Date: 2024-02-07 19:05:09.190089

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3acf3acab4bd'
down_revision = '5d5e9f9ee3c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('beneficiary_form', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('beneficiary_form', schema=None) as batch_op:
        batch_op.drop_column('uuid')

    # ### end Alembic commands ###
