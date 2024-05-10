"""added service date

Revision ID: cfed25d82162
Revises: 273fc35b80b9
Create Date: 2024-05-10 19:48:08.098656

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cfed25d82162'
down_revision = '273fc35b80b9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case_beneficiary', schema=None) as batch_op:
        batch_op.add_column(sa.Column('serviceDate', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case_beneficiary', schema=None) as batch_op:
        batch_op.drop_column('serviceDate')

    # ### end Alembic commands ###
