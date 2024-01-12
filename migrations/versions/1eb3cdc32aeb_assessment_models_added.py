"""assessment models added

Revision ID: 1eb3cdc32aeb
Revises: 2a9c00e0d22f
Create Date: 2024-01-12 22:21:24.252155

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1eb3cdc32aeb'
down_revision = '2a9c00e0d22f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('assessment_questions',
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('questionText', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('questionID')
    )
    op.create_table('assessment_answers',
    sa.Column('answerID', sa.Integer(), nullable=False),
    sa.Column('projectID', sa.Integer(), nullable=False),
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('answerText', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['projectID'], ['projects.projectID'], ),
    sa.ForeignKeyConstraint(['questionID'], ['assessment_questions.questionID'], ),
    sa.PrimaryKeyConstraint('answerID')
    )
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('order', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.drop_column('order')

    op.drop_table('assessment_answers')
    op.drop_table('assessment_questions')
    # ### end Alembic commands ###