"""sponsorAvailable

Revision ID: 243cc1689c33
Revises: 4a085feaa902
Create Date: 2024-02-03 09:32:43.059215

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '243cc1689c33'
down_revision = '4a085feaa902'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sponsorAvailable', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases_data', schema=None) as batch_op:
        batch_op.drop_column('sponsorAvailable')

    # ### end Alembic commands ###
