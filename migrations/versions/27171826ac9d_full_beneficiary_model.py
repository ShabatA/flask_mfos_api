"""full beneficiary model

Revision ID: 27171826ac9d
Revises: 92d2fbaecc2c
Create Date: 2024-02-11 16:58:11.826081

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "27171826ac9d"
down_revision = "92d2fbaecc2c"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("case_beneficiary", schema=None) as batch_op:
        batch_op.add_column(sa.Column("firstName", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("surName", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("phoneNumber", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("altPhoneNumber", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(), nullable=False))
        batch_op.add_column(sa.Column("serviceRequired", sa.String(), nullable=False))
        batch_op.add_column(
            sa.Column("otherServiceRequired", sa.String(), nullable=True)
        )
        batch_op.add_column(sa.Column("problemDescription", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("serviceDescription", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("totalSupportCost", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("receiveFundDate", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("paymentMethod", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("paymentsType", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("otherPaymentType", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("incomeType", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("otherIncomeType", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("housing", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("otherHousing", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("housingType", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("otherHousingType", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("totalFamilyMembers", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("childrenUnder15", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("isOldPeople", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("isDisabledPeople", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("isStudentsPeople", sa.Boolean(), nullable=True))
        batch_op.alter_column(
            "gender",
            existing_type=sa.INTEGER(),
            type_=sa.String(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "idType",
            existing_type=sa.INTEGER(),
            type_=sa.String(),
            existing_nullable=False,
        )
        batch_op.drop_column("surname")
        batch_op.drop_column("name")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("case_beneficiary", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False)
        )
        batch_op.add_column(
            sa.Column("surname", sa.VARCHAR(), autoincrement=False, nullable=False)
        )
        batch_op.alter_column(
            "idType",
            existing_type=sa.String(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "gender",
            existing_type=sa.String(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
        batch_op.drop_column("isStudentsPeople")
        batch_op.drop_column("isDisabledPeople")
        batch_op.drop_column("isOldPeople")
        batch_op.drop_column("childrenUnder15")
        batch_op.drop_column("totalFamilyMembers")
        batch_op.drop_column("otherHousingType")
        batch_op.drop_column("housingType")
        batch_op.drop_column("otherHousing")
        batch_op.drop_column("housing")
        batch_op.drop_column("otherIncomeType")
        batch_op.drop_column("incomeType")
        batch_op.drop_column("otherPaymentType")
        batch_op.drop_column("paymentsType")
        batch_op.drop_column("paymentMethod")
        batch_op.drop_column("receiveFundDate")
        batch_op.drop_column("totalSupportCost")
        batch_op.drop_column("serviceDescription")
        batch_op.drop_column("problemDescription")
        batch_op.drop_column("otherServiceRequired")
        batch_op.drop_column("serviceRequired")
        batch_op.drop_column("email")
        batch_op.drop_column("altPhoneNumber")
        batch_op.drop_column("phoneNumber")
        batch_op.drop_column("surName")
        batch_op.drop_column("firstName")

    # ### end Alembic commands ###
