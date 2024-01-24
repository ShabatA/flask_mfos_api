"""Update relationships and cascade options

Revision ID: 44c11d403d8e
Revises: a1f3751dd900
Create Date: 2024-01-24 12:47:57.135175

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '44c11d403d8e'
down_revision = 'a1f3751dd900'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # with op.batch_alter_table('cases', schema=None) as batch_op:
    #     batch_op.alter_column('category',
    #            existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
    #            type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
    #            existing_nullable=True)
    pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column('category',
               existing_type=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
               type_=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
               existing_nullable=True)

    # ### end Alembic commands ###
