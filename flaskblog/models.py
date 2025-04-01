from datetime import datetime
from flaskblog import db
from flask_login import UserMixin

#categories of posts
CATEGORIES = [
    ('food', 'Food'),
    ('electronics', 'Electronics'),
    ('clothing', 'Clothing'),
    ('books', 'Books'),
    ('beauty_service', 'Beauty_service'),
    ('cleaning', 'Cleaning'),
    ('general', 'General')
]

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    account_balance = db.Column(db.Float, default=0.0)  # Current available balance
    total_sales = db.Column(db.Float, default=0.0)      # Lifetime sales
    bank_account = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    phone_for_payment = db.Column(db.String(20), nullable=True)
    posts = db.relationship('Post', backref='author', lazy=True)


    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(20), nullable=False, default='')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_file = db.Column(db.String(20), nullable=True)
    cart_items = db.relationship('CartItem', backref='post', lazy=True)
    category = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)


    def __repr__(self):
        return f"CartItem('{self.user_id}', '{self.post_id}', '{self.quantity}')"

# models.py
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Recipient of the notification
    message = db.Column(db.String(255), nullable=False)  # Notification message
    is_read = db.Column(db.Boolean, default=False)  # Whether the notification has been read
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Notification('{self.user_id}', '{self.message}', '{self.is_read}')"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    tracking_id = db.Column(db.String(100), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, nullable=False)  # Your commission
    status = db.Column(db.String(30), default='pending')  # pending, completed, failed
    date_created = db.Column(db.DateTime, default=datetime.utcnow)


    # Relationship to buyer
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='purchases')

    # Relationship to transaction items
    items = db.relationship('TransactionItem', backref='transaction', cascade='all, delete-orphan')

class TransactionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    cart_item_id = db.Column(db.Integer, db.ForeignKey('cart_item.id'), nullable=False)  # ✅ Column is nullable=False
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    seller_amount = db.Column(db.Float, nullable=False)
    is_disbursed = db.Column(db.Boolean, default=False)
    disbursement_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    post = db.relationship('Post')
    seller = db.relationship('User', foreign_keys=[seller_id], backref='sales')
    cart_item = db.relationship('CartItem', backref='transaction_items')  # ✅ Relationship fixed
