"""Update the case table

Revision ID: cbc0330122a8
Revises: a9697b412ba6
Create Date: 2023-12-25 22:47:18.615742

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cbc0330122a8'
down_revision = 'a9697b412ba6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cquestions',
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('questionText', sa.String(), nullable=False),
    sa.Column('questionType', sa.String(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('questionID')
    )
    op.create_table('cquestion_choices',
    sa.Column('choiceID', sa.Integer(), nullable=False),
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('choiceText', sa.String(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['questionID'], ['cquestions.questionID'], ),
    sa.PrimaryKeyConstraint('choiceID')
    )
    op.create_table('canswers',
    sa.Column('answerID', sa.Integer(), nullable=False),
    sa.Column('caseID', sa.Integer(), nullable=False),
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('answerText', sa.String(), nullable=True),
    sa.Column('choiceID', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], ),
    sa.ForeignKeyConstraint(['choiceID'], ['cquestion_choices.choiceID'], ),
    sa.ForeignKeyConstraint(['questionID'], ['cquestions.questionID'], ),
    sa.PrimaryKeyConstraint('answerID')
    )
    op.create_table('case_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('caseID', sa.Integer(), nullable=False),
    sa.Column('userID', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], ),
    sa.ForeignKeyConstraint(['userID'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('serviceRequired', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('startDate', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('dueDate', sa.Date(), nullable=True))
        batch_op.alter_column('caseCategory',
               existing_type=sa.VARCHAR(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.alter_column('caseCategory',
               existing_type=sa.VARCHAR(),
               nullable=False)
        batch_op.drop_column('dueDate')
        batch_op.drop_column('startDate')
        batch_op.drop_column('serviceRequired')

    op.drop_table('case_users')
    op.drop_table('canswers')
    op.drop_table('cquestion_choices')
    op.drop_table('cquestions')
    # ### end Alembic commands ###
