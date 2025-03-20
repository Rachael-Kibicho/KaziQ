from flask import render_template, url_for, flash, redirect, request
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from flaskblog import app, db, bcrypt, socketio
from flaskblog.models import User, Post, Message, db, posts
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_migrate import Migrate
from datetime import datetime

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn



@app.route('/home')
@app.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.asc()).paginate(page=page, per_page=4)
    return render_template('home.html', posts=posts, title='Home')


@app.route('/about')
def about():
    return render_template('about.html', title = 'About')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Successfully logged in!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            print("Picture data:", form.picture.data)  # Debugging statement
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account updated successfully', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title = 'Account', image_file=image_file, form=form)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your Post has been created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_posts.html', title='New Post', form=form)

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, posts=post)

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
            .order_by(Post.date_posted.asc())\
            .paginate(page=page, per_page=4)

    return render_template('user_posts.html', title=user.username, posts=posts, user=user)


@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/chat/<int:user_id>')
@login_required
def private_chat(user_id):
    other_user = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id))
        |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.timestamp.asc()).all()

    return render_template('private_chat.html', other_user=other_user, messages=messages)


@socketio.on('private_message')
def handle_private_message(data):
    receiver_id = data['receiver_id']
    message = data['message']
    timestamp = datetime.utcnow().isoformat()

    # Save the message to the database
    new_message = Message(sender_id=current_user.id, receiver_id=receiver_id, content=message, timestamp=timestamp)
    db.session.add(new_message)
    db.session.commit()

    # Emit the message to the receiver
    emit('new_message', {
        'sender': current_user.username,
        'message': message,
        'timestamp': timestamp
    }, room=receiver_id)
