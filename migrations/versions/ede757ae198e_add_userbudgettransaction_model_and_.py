"""Add UserBudgetTransaction model and fund-to-user transfer

Revision ID: ede757ae198e
Revises: a8e6c3a2110d
Create Date: 2024-09-09 22:37:21.519515

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ede757ae198e'
down_revision = 'a8e6c3a2110d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_budget_transaction',
    sa.Column('transactionID', sa.Integer(), nullable=False),
    sa.Column('fromBudgetID', sa.Integer(), nullable=True),
    sa.Column('toBudgetID', sa.Integer(), nullable=True),
    sa.Column('fromFundID', sa.Integer(), nullable=True),
    sa.Column('transferAmount', sa.Float(), nullable=False),
    sa.Column('transferType', sa.String(length=50), nullable=False),
    sa.Column('currencyID', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('transferDate', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['currencyID'], ['currencies.currencyID'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['fromBudgetID'], ['user_budget.budgetId'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['fromFundID'], ['financial_fund.fundID'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['toBudgetID'], ['user_budget.budgetId'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('transactionID')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_budget_transaction')
    # ### end Alembic commands ###
