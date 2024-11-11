"""add translate model

Revision ID: 171464f8fc69
Revises: 362cb052191a
Create Date: 2024-11-10 22:31:16.106107

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '171464f8fc69'
down_revision = '362cb052191a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('translation_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('caseID', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('projectID', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'projects_data', ['projectID'], ['projectID'])
        batch_op.create_foreign_key(None, 'cases_data', ['caseID'], ['caseID'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('translation_requests', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('projectID')
        batch_op.drop_column('caseID')

    # ### end Alembic commands ###