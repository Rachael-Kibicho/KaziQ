from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from dotenv import load_dotenv
import os

load_dotenv()  # Loading environment variables from a .env file

STREAM_API_KEY = os.getenv("STREAM_API_KEY", "hx3bnnadbnhm")
STREAM_API_SECRET = os.getenv("STREAM_API_SECRET", "hs8knp6m893un45zaggqrn9mf4gvjxneyzqaust7nnudnv9jkrkg6gyp83kmhhzf")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'efb1507e69b6b364a5aab88e0f7d694c'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
socketio = SocketIO(app, cors_allowed_origins="*")

#Making sure CORS recognizes our url as an exception to the same-origin policy

CORS(app, origins=["http://localhost:5000"])  # Allow your frontend origin


from flaskblog.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flaskblog import routes

@app.context_processor
def inject_min_max():
    return dict(min=min, max=max)
