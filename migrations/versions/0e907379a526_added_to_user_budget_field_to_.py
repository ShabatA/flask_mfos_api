"""Added to_user_budget field to FundTransfers and adjusted nullability

Revision ID: 0e907379a526
Revises: ede757ae198e
Create Date: 2024-09-15 10:37:24.341418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0e907379a526'
down_revision = 'ede757ae198e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fund_transfers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('to_user_budget', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'user_budget', ['to_user_budget'], ['budgetId'], ondelete='CASCADE')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('fund_transfers', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('to_user_budget')

    # ### end Alembic commands ###
