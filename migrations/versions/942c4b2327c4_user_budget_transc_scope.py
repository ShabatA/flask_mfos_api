from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '942c4b2327c4'
down_revision = 'b5cb621f8468'
branch_labels = None
depends_on = None


def upgrade():
    # Create the TransactionScope enum type
    transaction_scope = postgresql.ENUM('USER', 'CASE', 'PROJECT', name='transactionscope')
    transaction_scope.create(op.get_bind())

    # Add the transactionScope column as nullable first
    with op.batch_alter_table('user_budget_transaction', schema=None) as batch_op:
        batch_op.add_column(sa.Column('transactionScope', sa.Enum('USER', 'CASE', 'PROJECT', name='transactionscope'), nullable=True))

    # Set a default value for existing rows
    op.execute(
        """
        UPDATE user_budget_transaction
        SET "transactionScope" = 'USER'
        """
    )

    # Alter the column to make it NOT NULL
    with op.batch_alter_table('user_budget_transaction', schema=None) as batch_op:
        batch_op.alter_column('transactionScope', nullable=False)


def downgrade():
    # Drop the transactionScope column
    with op.batch_alter_table('user_budget_transaction', schema=None) as batch_op:
        batch_op.drop_column('transactionScope')

    # Drop the TransactionScope enum type
    transaction_scope = postgresql.ENUM('USER', 'CASE', 'PROJECT', name='transactionscope')
    transaction_scope.drop(op.get_bind())
