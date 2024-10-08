"""added createdAt

Revision ID: b0edfc734f24
Revises: 44c11d403d8e
Create Date: 2024-01-24 21:40:11.062355

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b0edfc734f24"
down_revision = "44c11d403d8e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # with op.batch_alter_table('cases', schema=None) as batch_op:
    #     batch_op.alter_column('category',
    #            existing_type=postgresql.ENUM('A', 'B', 'C', 'D', name='cases_category'),
    #            type_=sa.Enum('A', 'B', 'C', 'D', name='casecategory'),
    #            existing_nullable=True)

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("createdAt", sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("createdAt")

    with op.batch_alter_table("cases", schema=None) as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.Enum("A", "B", "C", "D", name="casecategory"),
            type_=postgresql.ENUM("A", "B", "C", "D", name="cases_category"),
            existing_nullable=True,
        )

    # ### end Alembic commands ###
