"""add columns for email_sent to bookings table

Revision ID: 30c2613a634a
Revises: b5892f55e6d7
Create Date: 2023-04-20 16:42:20.107449

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '30c2613a634a'
down_revision = 'b5892f55e6d7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contentpack_bookings', sa.Column('email_sent_to_brand', sa.Boolean(), nullable=True))
    op.add_column('contentpack_bookings', sa.Column('email_sent_to_influencer', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('contentpack_bookings', 'email_sent_to_influencer')
    op.drop_column('contentpack_bookings', 'email_sent_to_brand')
    # ### end Alembic commands ###
