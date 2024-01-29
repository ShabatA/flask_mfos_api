"""new  case model

Revision ID: af9541d41f58
Revises: d3032b968590
Create Date: 2024-01-29 19:39:06.331940

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'af9541d41f58'
down_revision = 'd3032b968590'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cases_data',
    sa.Column('caseID', sa.Integer(), nullable=False),
    sa.Column('userID', sa.Integer(), nullable=False),
    sa.Column('regionID', sa.Integer(), nullable=True),
    sa.Column('caseName', sa.String(), nullable=False),
    sa.Column('question1', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question2', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question3', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question4', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question5', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question6', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question7', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question8', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question9', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('question10', sa.Integer(), nullable=False),
    sa.Column('question11', sa.Float(), nullable=False),
    sa.Column('question12', sa.Integer(), nullable=False),
    sa.Column('caseStatus', sa.Enum('PENDING', 'APPROVED', 'INPROGRESS', 'REJECTED', 'COMPLETED', 'ASSESSMENT', name='casestat'), nullable=False),
    sa.Column('category', sa.Enum('A', 'B', 'C', 'D', name='casecat'), nullable=True),
    sa.Column('createdAt', sa.DateTime(), nullable=False),
    sa.Column('startDate', sa.Date(), nullable=True),
    sa.Column('dueDate', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['regionID'], ['regions.regionID'], ),
    sa.ForeignKeyConstraint(['userID'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('caseID')
    )
    
    with op.batch_alter_table('beneficiary_form', schema=None) as batch_op:
        batch_op.drop_constraint('beneficiary_form_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_assessment_answers', schema=None) as batch_op:
        batch_op.drop_constraint('case_assessment_answers_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_beneficiary', schema=None) as batch_op:
        batch_op.drop_constraint('case_beneficiary_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_status_data', schema=None) as batch_op:
        batch_op.drop_constraint('case_status_data_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_task', schema=None) as batch_op:
        batch_op.drop_constraint('case_task_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_to_stage', schema=None) as batch_op:
        batch_op.drop_constraint('case_to_stage_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_users', schema=None) as batch_op:
        batch_op.drop_constraint('case_users_caseID_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    with op.batch_alter_table('projects_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totalPoints', sa.Integer(), nullable=True))
    op.drop_table('cases')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('projects_data', schema=None) as batch_op:
        batch_op.drop_column('totalPoints')

    with op.batch_alter_table('case_users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_users_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_to_stage', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_to_stage_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_task', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_task_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_status_data', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_status_data_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_beneficiary', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_beneficiary_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('case_assessment_answers', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('case_assessment_answers_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    with op.batch_alter_table('beneficiary_form', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('beneficiary_form_caseID_fkey', 'cases', ['caseID'], ['caseID'])

    op.create_table('cases',
    sa.Column('caseID', sa.INTEGER(), server_default=sa.text('nextval(\'"cases_caseID_seq"\'::regclass)'), autoincrement=True, nullable=False),
    sa.Column('caseName', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('caseStatus', postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', 'ASSESSMENT', name='casestatus'), autoincrement=False, nullable=False),
    sa.Column('userID', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('regionID', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('createdAt', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('startDate', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('dueDate', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('category', postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'), autoincrement=False, nullable=True),
    sa.Column('question1', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('question2', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('question3', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('question4', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question5', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question6', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question7', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question8', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question9', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('question10', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('question11', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('question12', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['regionID'], ['regions.regionID'], name='cases_regionID_fkey'),
    sa.ForeignKeyConstraint(['userID'], ['users.userID'], name='cases_userID_fkey'),
    sa.PrimaryKeyConstraint('caseID', name='cases_pkey')
    )
    op.drop_table('cases_data')
    # ### end Alembic commands ###
