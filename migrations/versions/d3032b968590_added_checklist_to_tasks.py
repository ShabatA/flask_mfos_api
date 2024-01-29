"""added checklist to tasks

Revision ID: d3032b968590
Revises: 93d938aea01a
Create Date: 2024-01-29 14:31:47.950866

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd3032b968590'
down_revision = '93d938aea01a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # with op.batch_alter_table('cases', schema=None) as batch_op:
    #     batch_op.alter_column('category',
    #            existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
    #            type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
    #            existing_nullable=True)

    with op.batch_alter_table('project_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project_task', schema=None) as batch_op:
        batch_op.drop_column('checklist')

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column('category',
               existing_type=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
               type_=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
               existing_nullable=True)

    with op.batch_alter_table('case_task', schema=None) as batch_op:
        batch_op.drop_column('checklist')

    # ### end Alembic commands ###
