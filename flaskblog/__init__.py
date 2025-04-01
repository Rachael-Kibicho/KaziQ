from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from engineio.async_drivers import gevent


from dotenv import load_dotenv
import os

load_dotenv()

# Secrets (use environment variables)
STREAM_API_KEY = os.getenv("STREAM_API_KEY", "hx3bnnadbnhm")
STREAM_API_SECRET = os.getenv("STREAM_API_SECRET", "hs8knp6m893un45zaggqrn9mf4gvjxneyzqaust7nnudnv9jkrkg6gyp83kmhhzf")
PESAPAL_CONSUMER_KEY = os.getenv("PESAPAL_CONSUMER_KEY", "KHyCbxCmYCzi6OG/UnK0dZFc+T16NzJ1")
PESAPAL_CONSUMER_SECRET = os.getenv("PESAPAL_CONSUMER_SECRET", "WU+ubs2hxYDpWHPx5BlOALtlFCI=")

app = Flask(__name__)
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY', 'efb1507e69b6b364a5aab88e0f7d694c'),
    'SESSION_TYPE': 'sqlalchemy',
    'SESSION_COOKIE_SECURE': False,  # Set to True in production
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'REMEMBER_COOKIE_SAMESITE': 'Lax',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///site.db',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
})

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# CORS Configuration
CORS(app, origins=["http://localhost:5000"], supports_credentials=True)

# SocketIO Configuration

packages = []
packages += ['engineio', 'socketio', 'flask_socketio', 'threading', 'time', 'queue','eventlet', 'gevent']

socketio = SocketIO(
    app,
    cors_allowed_origins="http://localhost:5000",
    logging=True,
    engineio_logger=True,
    async_mode='eventlet'
)

from flaskblog.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flaskblog import routes

@app.context_processor
def inject_min_max():
    return dict(min=min, max=max)

from flask import current_app
from datetime import datetime

def format_currency(value):
    return f"{current_app.config['CURRENCY']} {value:,.2f}"

def format_datetime(value):
    if not value:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M")

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
