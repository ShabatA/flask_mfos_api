"""changed document type

Revision ID: ca6cbc2d9dd4
Revises: fb64335f2955
Create Date: 2024-01-28 16:37:29.673526

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ca6cbc2d9dd4'
down_revision = 'fb64335f2955'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # with op.batch_alter_table('cases', schema=None) as batch_op:
    #     batch_op.alter_column('category',
    #            existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
    #            type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
    #            existing_nullable=True)

    with op.batch_alter_table('projects_data', schema=None) as batch_op:
        batch_op.alter_column('documents',
               existing_type=postgresql.ARRAY(sa.INTEGER()),
               type_=postgresql.ARRAY(sa.String()),
               existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('projects_data', schema=None) as batch_op:
        batch_op.alter_column('documents',
               existing_type=postgresql.ARRAY(sa.String()),
               type_=postgresql.ARRAY(sa.INTEGER()),
               existing_nullable=True)

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column('category',
               existing_type=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
               type_=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
               existing_nullable=True)

    # ### end Alembic commands ###
