"""increase bio char limit

Revision ID: 80839f7c48f3
Revises: 11058111dab5
Create Date: 2022-09-08 21:55:22.290392

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80839f7c48f3'
down_revision = '11058111dab5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('target_user_profile', 'bio',
               existing_type=sa.VARCHAR(length=400),
               type_=sa.String(length=600),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('target_user_profile', 'bio',
               existing_type=sa.String(length=600),
               type_=sa.VARCHAR(length=400),
               existing_nullable=False)
    # ### end Alembic commands ###