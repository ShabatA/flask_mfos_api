"""case models altered

Revision ID: 18258840e30e
Revises: f3f037771a16
Create Date: 2024-01-16 23:16:34.328326

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '18258840e30e'
down_revision = 'f3f037771a16'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('case_assessment_questions',
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('questionText', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('questionID')
    )
    op.create_table('case_assessment_answers',
    sa.Column('answerID', sa.Integer(), nullable=False),
    sa.Column('caseID', sa.Integer(), nullable=False),
    sa.Column('questionID', sa.Integer(), nullable=False),
    sa.Column('answerText', sa.String(), nullable=True),
    sa.Column('extras', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['caseID'], ['cases.caseID'], ),
    sa.ForeignKeyConstraint(['questionID'], ['case_assessment_questions.questionID'], ),
    sa.PrimaryKeyConstraint('answerID')
    )
    with op.batch_alter_table('canswers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('extras', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add 'ASSESSMENT' to the enum
    op.execute("COMMIT;")
    op.execute("ALTER TYPE casestatus ADD VALUE 'ASSESSMENT';")
    op.execute("BEGIN;")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('canswers', schema=None) as batch_op:
        batch_op.drop_column('extras')

    op.drop_table('case_assessment_answers')
    op.drop_table('case_assessment_questions')
    # ### end Alembic commands ###
