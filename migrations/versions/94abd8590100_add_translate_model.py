"""add translate model

Revision ID: 94abd8590100
Revises: 212016d5f57a
Create Date: 2024-11-10 15:33:28.097189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94abd8590100'
down_revision = '212016d5f57a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('contents',
    sa.Column('content_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_on', sa.DateTime(), nullable=True),
    sa.Column('service_description', sa.Text(), nullable=True),
    sa.Column('documents', sa.Text(), nullable=True),
    sa.Column('recommendations', sa.Text(), nullable=True),
    sa.Column('credit_info', sa.Text(), nullable=True),
    sa.Column('media_note', sa.Text(), nullable=True),
    sa.Column('translations', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('content_id')
    )
    op.create_table('translation_requests',
    sa.Column('request_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=False),
    sa.Column('requested_by_id', sa.Integer(), nullable=False),
    sa.Column('translator_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('pending', 'in_progress', 'completed'), nullable=True),
    sa.Column('requested_on', sa.DateTime(), nullable=True),
    sa.Column('completed_on', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['content_id'], ['contents.content_id'], ),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.userID'], ),
    sa.ForeignKeyConstraint(['translator_id'], ['users.userID'], ),
    sa.PrimaryKeyConstraint('request_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('translation_requests')
    op.drop_table('contents')
    # ### end Alembic commands ###
