"""change user_id to user_email

Revision ID: 6e48227dbe49
Revises: a5b621570043
Create Date: 2023-04-11 12:00:21.840602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e48227dbe49'
down_revision = 'a5b621570043'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contentpacks_user_map', sa.Column('user_email', sa.String(), nullable=False))
    op.drop_column('contentpacks_user_map', 'user_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contentpacks_user_map', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_column('contentpacks_user_map', 'user_email')
    # ### end Alembic commands ###