"""Create OTPRequest table

Revision ID: 3289b145e0ad
Revises: 70d74a4d29c2
Create Date: 2024-11-09 10:25:24.220158

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3289b145e0ad'
down_revision = '70d74a4d29c2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('otp_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('otp', sa.String(), nullable=False),
    sa.Column('expiration_time', sa.DateTime(), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('otp_requests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_otp_requests_id'), ['id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('otp_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_otp_requests_id'))

    op.drop_table('otp_requests')
    # ### end Alembic commands ###
