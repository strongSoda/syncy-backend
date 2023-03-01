"""create influencer profile table

Revision ID: 9c9e0dbac85d
Revises: d83e1e11b59a
Create Date: 2023-03-01 18:11:26.883470

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c9e0dbac85d'
down_revision = 'd83e1e11b59a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('influencer_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_modified', sa.DateTime(), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('first_name', sa.String(length=200), nullable=True),
    sa.Column('last_name', sa.String(length=200), nullable=True),
    sa.Column('bio', sa.String(length=200), nullable=True),
    sa.Column('city', sa.String(length=200), nullable=True),
    sa.Column('image_url', sa.String(length=200), nullable=True),
    sa.Column('calender_url', sa.String(length=200), nullable=True),
    sa.Column('instagram_username', sa.String(length=200), nullable=True),
    sa.Column('followers_count', sa.Integer(), nullable=True),
    sa.Column('rate', sa.Integer(), nullable=True),
    sa.Column('category', sa.String(length=200), nullable=True),
    sa.Column('hashtags', sa.String(length=200), nullable=True),
    sa.Column('top_post_url_1', sa.String(length=200), nullable=True),
    sa.Column('top_post_url_2', sa.String(length=200), nullable=True),
    sa.Column('top_post_url_3', sa.String(length=200), nullable=True),
    sa.Column('sponsored_post_url_1', sa.String(length=200), nullable=True),
    sa.Column('sponsored_post_url_2', sa.String(length=200), nullable=True),
    sa.Column('sponsored_post_url_3', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('influencer_profile')
    # ### end Alembic commands ###
