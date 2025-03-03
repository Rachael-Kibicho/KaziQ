
#dummy data now
posts = [
    {
        'author':'JewelleryByAnnu 💍',
        'title': 'Bracelets',
        'content': 'We have new bracelets in stock. Check them out!',
        'date': '14th February 2013'
    },
    {
        'author':'HomeGrown Groceries 🥑',
        'title': 'Avocados',
        'content': 'We have fresh avocados right from the tree. Buy while stocks last!',
        'date': '15th March 2010'

    },
        {
        'author':'Lock It 👩🏾‍🦱' ,
        'title': 'Microlock Extensions',
        'content': "Don't want to start locks with short hair, we got you!",
        'date': '15th March 2010'

    }
]
from datetime import datetime
from flaskblog import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"
