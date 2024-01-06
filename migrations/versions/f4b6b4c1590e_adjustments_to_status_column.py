"""Adjustments to status column

Revision ID: f4b6b4c1590e
Revises: f9c18d8f53f2
Create Date: 2024-01-06 20:18:00.677792

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4b6b4c1590e'
down_revision = 'f9c18d8f53f2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('userID', sa.Integer(), nullable=False),
    sa.Column('taskID', sa.Integer(), nullable=False),
    sa.Column('comment', sa.String(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['taskID'], ['project_task.taskID'], ),
    sa.ForeignKeyConstraint(['userID'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('project_task', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=postgresql.ENUM('TODO', 'INPROGRESS', 'DONE', 'OVERDUE', name='taskstatus'),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project_task', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=postgresql.ENUM('TODO', 'INPROGRESS', 'DONE', 'OVERDUE', name='taskstatus'),
               nullable=True)

    op.drop_table('task_comments')
    # ### end Alembic commands ###
