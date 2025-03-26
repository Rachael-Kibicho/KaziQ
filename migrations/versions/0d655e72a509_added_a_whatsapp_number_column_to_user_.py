"""Added a whatsapp number column to user and also price column to post

Revision ID: 0d655e72a509
Revises: a6cae5c99a1c
Create Date: 2025-03-26 20:28:28.488778

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d655e72a509'
down_revision = 'a6cae5c99a1c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('post', schema=None) as batch_op:
        # Add the 'price' column with a default value of 0
        batch_op.add_column(sa.Column('price', sa.Integer(), nullable=True, server_default='0'))

    # Update all existing rows to have a default value for 'price'
    op.execute('UPDATE post SET price = 0')

    with op.batch_alter_table('post', schema=None) as batch_op:
        # Make the 'price' column NOT NULL
        batch_op.alter_column('price', nullable=False, server_default=None)

    with op.batch_alter_table('user', schema=None) as batch_op:
        # Add the 'whatsapp' column with a default value
        batch_op.add_column(sa.Column('whatsapp', sa.String(length=20), nullable=True, server_default='Not Provided'))

    # Update all existing rows to have a default value for 'whatsapp'
    op.execute("UPDATE user SET whatsapp = 'Not Provided'")

    with op.batch_alter_table('user', schema=None) as batch_op:
        # Make the 'whatsapp' column NOT NULL
        batch_op.alter_column('whatsapp', nullable=False, server_default=None)
