import requests
from flask import render_template, url_for, flash, redirect, request, jsonify, abort
from stream_chat import StreamChat
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from flaskblog import app, db, bcrypt, STREAM_API_KEY, STREAM_API_SECRET
from flaskblog.models import User, Post, CartItem, db, posts
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image
from flask_migrate import Migrate
from datetime import datetime

#HTML routes

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    # Resize the image before saving it
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

def save_post_image(form_image):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_image.filename)
    image_fn = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/post_images', image_fn)

    # Resizing the image before saving it
    output_size = (250, 250)
    img = Image.open(form_image)
    img.thumbnail(output_size)
    img.save(image_path)

    print("FormImage:", form_image)

    return image_fn


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
        if form.image.data:
            print("Image data received:", form.image.data)  # Debugging statement
            image_file = save_post_image(form.image.data)
            print("Image filename has been saved:", image_file)
        else:
            print("No image uploaded, sorry!")
            image_file = None

        post = Post(title=form.title.data, content=form.content.data,author=current_user, image_file=image_file)
        db.session.add(post)
        db.session.commit()
        flash('Your Post has been created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_posts.html', title='New Post', form=form)

@app.route("/post/<int:post_id>")
def post(post_id):
    posts = Post.query.get_or_404(post_id)
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('post.html', title=posts.title, posts=posts, cart_items=cart_items)

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
            .order_by(Post.date_posted.asc())\
            .paginate(page=page, per_page=4)

    return render_template('user_posts.html', title=user.username, posts=posts, user=user)


#CHAT ROUTES

@app.route('/generate-stream-token')
@login_required
def generate_stream_token():
    user_id = str(current_user.id)
    token = client.create_token(user_id)
    return jsonify({"token": token})

# Initialize Stream Chat
client = StreamChat(api_key=str(STREAM_API_KEY), api_secret=str(STREAM_API_SECRET))

@app.route('/chat/<int:user_id>')
@login_required
def private_chat(user_id):
    other_user = User.query.get_or_404(user_id)
    channel_id = f"{min(current_user.id, user_id)}-{max(current_user.id, user_id)}"

    try:
        channel = client.channel("messaging", channel_id)
        channel_state = channel.query()
        #Ensure the channel is set up with an owner
        channel.update({"created_by_id": str(current_user.id)})
    except Exception as e:
        channel = client.channel("messaging", channel_id, {
            "created_by_id": str(current_user.id)
        })
        channel.create(current_user.id)

    return render_template('private_chat.html',
        title='Chat',
        other_user=other_user,
        stream_api_key=STREAM_API_KEY,
        channel_id=channel_id,
    )

@app.route("/get_channel")
def get_channel():
    headers = {"Authorization": "Bearer YOUR_STREAM_API_SECRET"}
    response = requests.get("https://chat.stream-io-api.com/some-endpoint", headers=headers)
    return response.json()

# SEARCH ROUTE

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')  # Get the search query from the URL
    if not query:
        return redirect(url_for('home'))  # Redirect to home if no query is provided

    # Perform a database search (example: searching posts by title)
    results = Post.query.filter(Post.title.ilike(f"%{query}%")).all()

    return render_template('search_results.html', query=query, results=results)


@app.route('/add_to_cart/<int:post_id>', methods=['POST'])
@login_required
def add_to_cart(post_id):
    post = Post.query.get_or_404(post_id)
    cart_item = CartItem.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, post_id=post.id)
        db.session.add(cart_item)

    db.session.commit()
    flash(f"Added {post.title} to your cart!", "success")
    return redirect(url_for('home', post_id=post.id))


@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', title='Your Cart', cart_items=cart_items)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    if cart_item.user_id != current_user.id:
        abort(403)  # Prevent unauthorized access

    db.session.delete(cart_item)
    db.session.commit()
    flash("Item removed from your cart.", "success")
    return redirect(url_for('view_cart'))
