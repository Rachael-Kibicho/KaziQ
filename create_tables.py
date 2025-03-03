from flaskblog import app, db
from flaskblog.models import User, Post

with app.app_context():
    db.create_all()
