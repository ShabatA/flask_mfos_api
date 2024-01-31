"""new project task

Revision ID: a1f3751dd900
Revises: aa42d6765ec9
Create Date: 2024-01-24 12:26:28.513777

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1f3751dd900'
down_revision = 'aa42d6765ec9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_task_assigned_to',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['project_task.taskID'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('project_task_cc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['project_task.taskID'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('task_cc')
    op.drop_table('task_assigned_to')
    with op.batch_alter_table('c_task_assigned_to', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.Integer(), nullable=False))

    with op.batch_alter_table('c_task_cc', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.Integer(), nullable=False))

    # with op.batch_alter_table('cases', schema=None) as batch_op:
    #     batch_op.alter_column('category',
    #            existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
    #            type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
    #            existing_nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column('category',
               existing_type=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
               type_=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
               existing_nullable=True)

    with op.batch_alter_table('c_task_cc', schema=None) as batch_op:
        batch_op.drop_column('id')

    with op.batch_alter_table('c_task_assigned_to', schema=None) as batch_op:
        batch_op.drop_column('id')

    op.create_table('task_assigned_to',
    sa.Column('task_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['project_task.taskID'], name='task_assigned_to_task_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.userID'], name='task_assigned_to_user_id_fkey')
    )
    op.create_table('task_cc',
    sa.Column('task_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['project_task.taskID'], name='task_cc_task_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.userID'], name='task_cc_user_id_fkey')
    )
    op.drop_table('project_task_cc')
    op.drop_table('project_task_assigned_to')
    # ### end Alembic commands ###