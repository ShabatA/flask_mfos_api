"""new case model

Revision ID: 93d938aea01a
Revises: ca6cbc2d9dd4
Create Date: 2024-01-29 12:37:35.595946

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '93d938aea01a'
down_revision = 'ca6cbc2d9dd4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('beneficiary_form',
    sa.Column('formID', sa.Integer(), nullable=False),
    sa.Column('caseID', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], ),
    sa.PrimaryKeyConstraint('formID')
    )
    op.create_table('case_beneficiary',
    sa.Column('beneficiaryID', sa.Integer(), nullable=False),
    sa.Column('caseID', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], ),
    sa.PrimaryKeyConstraint('beneficiaryID')
    )
    op.drop_table('canswers')
    op.drop_table('cquestion_choices')
    op.drop_table('cquestions')
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('question1', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('question2', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('question3', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('question4', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question5', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question6', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question7', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question8', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question9', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
        batch_op.add_column(sa.Column('question10', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('question11', sa.Float(), nullable=False))
        batch_op.add_column(sa.Column('question12', sa.String(), nullable=False))
        batch_op.alter_column('caseStatus',
               existing_type=postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', 'ASSESSMENT', name='casestatus'),
               nullable=False)
       #  batch_op.alter_column('category',
       #         existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
       #         type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
       #         existing_nullable=True)
        batch_op.drop_column('budgetAvailable')
        batch_op.drop_column('serviceRequired')
        batch_op.drop_column('budgetRequired')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('budgetRequired', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('serviceRequired', sa.VARCHAR(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('budgetAvailable', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
        batch_op.alter_column('category',
               existing_type=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
               type_=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
               existing_nullable=True)
        batch_op.alter_column('caseStatus',
               existing_type=postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', 'ASSESSMENT', name='casestatus'),
               nullable=True)
        batch_op.drop_column('question12')
        batch_op.drop_column('question11')
        batch_op.drop_column('question10')
        batch_op.drop_column('question9')
        batch_op.drop_column('question8')
        batch_op.drop_column('question7')
        batch_op.drop_column('question6')
        batch_op.drop_column('question5')
        batch_op.drop_column('question4')
        batch_op.drop_column('question3')
        batch_op.drop_column('question2')
        batch_op.drop_column('question1')

    op.create_table('cquestions',
    sa.Column('questionID', sa.INTEGER(), server_default=sa.text('nextval(\'"cquestions_questionID_seq"\'::regclass)'), autoincrement=True, nullable=False),
    sa.Column('questionText', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('questionType', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('points', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('order', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('questionID', name='cquestions_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('canswers',
    sa.Column('answerID', sa.INTEGER(), server_default=sa.text('nextval(\'"canswers_answerID_seq"\'::regclass)'), autoincrement=True, nullable=False),
    sa.Column('caseID', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('questionID', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('answerText', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('choiceID', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('extras', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], name='canswers_caseID_fkey'),
    sa.ForeignKeyConstraint(['choiceID'], ['cquestion_choices.choiceID'], name='canswers_choiceID_fkey'),
    sa.ForeignKeyConstraint(['questionID'], ['cquestions.questionID'], name='canswers_questionID_fkey'),
    sa.PrimaryKeyConstraint('answerID', name='canswers_pkey')
    )
    op.create_table('cquestion_choices',
    sa.Column('choiceID', sa.INTEGER(), server_default=sa.text('nextval(\'"cquestion_choices_choiceID_seq"\'::regclass)'), autoincrement=True, nullable=False),
    sa.Column('questionID', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('choiceText', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('points', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['questionID'], ['cquestions.questionID'], name='cquestion_choices_questionID_fkey'),
    sa.PrimaryKeyConstraint('choiceID', name='cquestion_choices_pkey')
    )
    op.drop_table('case_beneficiary')
    op.drop_table('beneficiary_form')
    # ### end Alembic commands ###
