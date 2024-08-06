"""request status

Revision ID: 38ac3dab1bcf
Revises: 866e1764e4f5
Create Date: 2024-07-28 11:10:01.196070

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '38ac3dab1bcf'
down_revision = '866e1764e4f5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case_fund_release_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), nullable=True))

    

    with op.batch_alter_table('project_fund_release_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project_fund_release_requests', schema=None) as batch_op:
        batch_op.drop_column('status')

    

    with op.batch_alter_table('case_fund_release_requests', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###