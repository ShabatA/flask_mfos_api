"""made adjustments from finance ui comments

Revision ID: 0a22594ad801
Revises: 1b4657d490d6
Create Date: 2024-02-28 20:57:24.365908

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0a22594ad801"
down_revision = "1b4657d490d6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("financial_fund", schema=None) as batch_op:
        batch_op.add_column(sa.Column("currency", sa.String(), nullable=True))

    with op.batch_alter_table("fund_transfer_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("currencyFrom", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("currencyTo", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("exchangeRate", sa.Float(), nullable=True))

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("currency", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("transferExpenses", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("exchangeRate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("supportingFiles", sa.String(), nullable=True))

    with op.batch_alter_table("region_account", schema=None) as batch_op:
        batch_op.add_column(sa.Column("currency", sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("region_account", schema=None) as batch_op:
        batch_op.drop_column("currency")

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_column("supportingFiles")
        batch_op.drop_column("exchangeRate")
        batch_op.drop_column("transferExpenses")
        batch_op.drop_column("currency")

    with op.batch_alter_table("fund_transfer_requests", schema=None) as batch_op:
        batch_op.drop_column("exchangeRate")
        batch_op.drop_column("currencyTo")
        batch_op.drop_column("currencyFrom")

    with op.batch_alter_table("financial_fund", schema=None) as batch_op:
        batch_op.drop_column("currency")

    # ### end Alembic commands ###
