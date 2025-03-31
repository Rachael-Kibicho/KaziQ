"""Added transaction tables and user columns

Revision ID: e719fcd3f0fe
Revises: 0d655e72a509
Create Date: 2025-03-30 14:24:52.431174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e719fcd3f0fe'
down_revision = '0d655e72a509'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transaction',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.String(length=100), nullable=False),
    sa.Column('tracking_id', sa.String(length=100), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=False),
    sa.Column('total_amount', sa.Float(), nullable=False),
    sa.Column('platform_fee', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['buyer_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cart_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('transaction_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.Integer(), nullable=False),
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('seller_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('seller_amount', sa.Float(), nullable=False),
    sa.Column('is_disbursed', sa.Boolean(), nullable=True),
    sa.Column('disbursement_date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.ForeignKeyConstraint(['quantity'], ['post.price'], ),
    sa.ForeignKeyConstraint(['seller_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('user_backup')
    op.drop_table('_alembic_tmp_post')
    op.drop_table('post_backup')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_balance', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('total_sales', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bank_account', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('bank_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('phone_for_payment', sa.String(length=20), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('phone_for_payment')
        batch_op.drop_column('bank_name')
        batch_op.drop_column('bank_account')
        batch_op.drop_column('total_sales')
        batch_op.drop_column('account_balance')

    op.create_table('post_backup',
    sa.Column('id', sa.INTEGER(), nullable=True),
    sa.Column('title', sa.TEXT(), nullable=True),
    sa.Column('date_posted', sa.NUMERIC(), nullable=True),
    sa.Column('content', sa.TEXT(), nullable=True),
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('image_file', sa.TEXT(), nullable=True)
    )
    op.create_table('_alembic_tmp_post',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('title', sa.VARCHAR(length=100), nullable=False),
    sa.Column('date_posted', sa.DATETIME(), nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('image_file', sa.VARCHAR(length=20), nullable=True),
    sa.Column('price', sa.INTEGER(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_backup',
    sa.Column('id', sa.INTEGER(), nullable=True),
    sa.Column('username', sa.TEXT(), nullable=True),
    sa.Column('email', sa.TEXT(), nullable=True),
    sa.Column('image_file', sa.TEXT(), nullable=True),
    sa.Column('password', sa.TEXT(), nullable=True)
    )
    op.drop_table('transaction_item')
    op.drop_table('cart_item')
    op.drop_table('transaction')
    # ### end Alembic commands ###
