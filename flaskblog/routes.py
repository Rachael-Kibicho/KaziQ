import hashlib
import uuid
import requests
import json
from flask import current_app, make_response, render_template, send_file, url_for, flash, redirect, request, jsonify, abort, session
import time
from stream_chat import StreamChat
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, UpdatePostForm
from flaskblog import app, db, bcrypt, STREAM_API_KEY, STREAM_API_SECRET
from flaskblog.models import User, Post, CartItem, Notification, Transaction, TransactionItem, db, CATEGORIES
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image
from flask_migrate import Migrate
from datetime import datetime
from requests_oauthlib import OAuth1
import requests
import logging
import pdfkit



config = pdfkit.configuration(
    wkhtmltopdf=r'C:/Users/pc/Downloads/wkhtmltox-0.12.6-1.msvc2015-win64.exe'
)



# For payments commission:
PLATFORM_FEE_PERCENTAGE = 5

# #HTML routes

#A few useful functions to be used in the routes

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


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
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=4, error_out=False)
    return render_template('home.html', posts=posts, categories=CATEGORIES)




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
        user = User(username=form.username.data, email=form.email.data, whatsapp=str(form.whatsapp), password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for "{form.username.data}!", "success"')
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
    print(f"Current User: {current_user}")  # Debugging statement
    print(f"Is Authenticated: {current_user.is_authenticated}")  # Debugging statement
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
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
    return render_template('account.html', title='Account', image_file=image_file, form=form)

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

        post = Post(title=form.title.data,
                    content=form.content.data,
                    price=form.price.data,
                    author=current_user,
                    image_file=image_file,
                    category=form.category.data)  # ADDED CATEGORY HERE
        db.session.add(post)
        db.session.commit()
        flash('Your Post has been created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)

@app.route("/post/<int:post_id>")
@login_required
def post(post_id):
    post = Post.query.get_or_404(post_id)
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('post.html', title=post.title, posts=post, cart_items=cart_items)

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
            .order_by(Post.date_posted.asc())\
            .paginate(page=page, per_page=4)

    return render_template('user_posts.html', title=user.username, posts=posts, user=user)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_posts(post_id):
    post = Post.query.get_or_404(post_id)

    # Ensure only the post owner can edit
    if post.author != current_user:
        flash("You don't have permission to edit this post.", "danger")
        return redirect(url_for('post', post_id=post.id))

    form = PostForm()  # Use PostForm instead of UpdatePostForm
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.price = form.price.data
        post.category = form.category.data

        if form.image.data:
            image_file = save_post_image(form.image.data)
            post.image_file = image_file

        db.session.commit()  # No need for db.session.add(post) here
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))

    elif request.method == 'GET':
        # Populate form fields with existing post data
        form.title.data = post.title
        form.content.data = post.content
        form.price.data = post.price
        form.category.data = post.category  # Set category value

    return render_template('update_post.html',
                           title='Update Post',
                           form=form,
                           legend='Update Post',
                           post_id=post.id)  # Pass post_id explicitly


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Ensure only the post owner can delete
    if post.author != current_user:
        flash("You don't have permission to delete this post.", "danger")
        return redirect(url_for('post', post_id=post.id))

    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')

    return redirect(url_for('home'))




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
    # Get the other user from the database
    other_user = User.query.get_or_404(user_id)

    # Create a unique channel ID for the chat
    channel_id = f"{min(current_user.id, user_id)}-{max(current_user.id, user_id)}"

    # Create or get the Stream Chat channel
    channel = client.channel("messaging", channel_id, {
        "created_by_id": str(current_user.id)
    })

    try:
        # Query the channel to fetch its state and messages
        channel_state = channel.query()
        messages = channel_state["messages"]  # Retrieve all messages from the channel

    except Exception as e:
        # If the channel doesn't exist, create it
        channel.create({"created_by_id": str(current_user.id)})
        messages = []  # No messages yet in a newly created channel

    return render_template(
        'private_chat.html',
        other_user=other_user,
        stream_api_key=STREAM_API_KEY,
        channel_id=channel_id,
        messages=messages
    )


@app.route('/notifications')
@login_required
def notifications():
    # Example logic for fetching notifications
    user_notifications = [
        {"message": "Someone wants to chat!"}
    ]
    return jsonify(user_notifications)


@app.route('/stream-webhook', methods=['POST'])
def stream_webhook():
    data = request.json

    if data.get("type") == "message.new":
        recipient_id = data["user"]["id"]
        message_text = data["text"]

        send_push_notification(recipient_id, f"New message: {message_text}")

    return jsonify({"success": True})


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

    return render_template('search_results.html', title='Search', query=query, results=results)

@app.route("/filter")
def filter_by_category():
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)

    if category:
        results = Post.query.filter_by(category=category).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    else:
        return redirect(url_for('home'))

    return render_template('search_results.html',
                           query=category,
                          results=results)


#-----CART SECTION--------
@app.route('/add_to_cart/<int:post_id>', methods=['GET','POST'])
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

    # Clear existing tracking ID when cart changes
    session.pop('current_tracking_id', None)
    session.pop('current_cart_signature', None)

    flash(f"Added '{post.title}!' to your cart!", "success")
    return redirect(url_for('view_cart', post_id=post.id))


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

    # Clear existing tracking ID when cart changes
    session.pop('current_tracking_id', None)
    session.pop('current_cart_signature', None)

    flash("Item removed from your cart.", "success")
    return redirect(url_for('view_cart'))


#-----TRANSACTION SECTION--------
@app.route('/transaction/<int:transaction_id>')
@login_required
def transaction_details(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    transaction_items = TransactionItem.query.filter_by(transaction_id=transaction_id).all()
    return render_template('transaction_details.html', transaction=transaction, transaction_items=transaction_items)

#-----RECEIPT SECTION--------


# Report generation routes

#Report for registered businsesses
@app.route('/report/registered_businesses')
@login_required

def registered_businesses_report():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("You are not authorized to access this page", "warning")
        return redirect(url_for('home'))
    users = User.query.all()
    return render_template('registered_business_report.html', users=users)

#Report for messaging activity
@app.route('/report/chat_activity')
@login_required

def chat_activity_report():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("You are not authorized to access this page", "warning")
        return redirect(url_for('home'))


    # Fetch total messages sent by each user
    messages_report = db.session.query(
        User.username,
        db.func.count(Notification.id).label('total_notifications')
    ).outerjoin(Notification, Notification.user_id == User.id) \
     .group_by(User.id).all()

    # Fetch total private chats initiated by each user
    private_chats_report = db.session.query(
        User.username,
        db.func.count(CartItem.id).label('total_private_chats')
    ).join(CartItem, CartItem.user_id == User.id) \
     .group_by(User.id).all()

    return render_template('chat_activity_report.html', messages_report=messages_report)

#Report for cart activity
@app.route('/report/cart_activity')
@login_required
def cart_activity_report():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("You are not authorized to access this page", "warning")
        return redirect(url_for('home'))

    # Total number of items in carts
    total_items = db.session.query(db.func.count(CartItem.id)).scalar()

    # Total number of unique users with items in their carts
    unique_users = db.session.query(CartItem.user_id).distinct().count()

    # Total quantity of items in all carts
    total_quantity = db.session.query(db.func.sum(CartItem.quantity)).scalar()

    return render_template('cart_activity_report.html', total_items=total_items, unique_users=unique_users, total_quantity=total_quantity)

#-----SALES REPORT SECTION--------
@app.route('/report/sales')
@login_required
def sales_report():
     admin_required()

     #Fetch all transactions
     transactions = Transaction.query.all()

     #Prepare data for the template
     sales_data = []
     total_revenue = 0

     for transaction in transactions:
          total_revenue += transaction.total_amount
          sales_data.append({
               'transaction_id': transaction.id,
               'user': transaction.buyer_id,
               'amount': transaction.total_amount,
               'date_created': transaction.date_created,
          })

     return render_template('sales_report.html', sales_data=sales_data, total_revenue=total_revenue)

# Pythoneer
# ======== PesaPal Service Class ========
class PesaPal:
    def __init__(self):
        self.base_url = "https://cybqa.pesapal.com/pesapalv3/api"
        self.token = None

    def authenticate(self):
        """Handle authentication with retry logic"""
        try:
            if self.token:  # Reuse existing token if valid
                return self.token

            endpoint = "Auth/RequestToken"

            # NOT SO SECURE, BUT WE MAKE IT WORK THEN WE MAKE IT BETTER..

            payload = {
                "consumer_key": "qkio1BGGYAXTu2JOfm7XSXNruoZsrqEW",
                "consumer_secret": "osGQ364R49cXKeOYSpaOnT++rHs="
            }

            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers={'Accept': 'application/json'}
            )

            response.raise_for_status()
            self.token = response.json()['token']
            return self.token

        except Exception as e:
            logging.exception("Authentication Error")
            self.token = None
            raise

    def submit_order(self, payment_data):
        endpoint = 'Transactions/SubmitOrderRequest'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.authenticate()}"
        }

        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payment_data,
                headers=headers
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            # Extract actual redirect URL from Pesapal's response
            redirect_url = data.get('call_back_url') or data.get('redirect_url')
            return {
                "redirect_url": redirect_url,
                "order_tracking_id": data.get('order_tracking_id'),
                "status": data.get('status')
            }
        except requests.exceptions.RequestException as e:
            logging.exception(f"Request Exception: {e}")
            raise  # Re-raise the exception to be handled in the route
        except (ValueError, KeyError) as e:
            logging.exception(f"JSON decoding or key error: {e}")
            raise
        except Exception as e:
            logging.exception(f"Unexpected error: {e}")
            raise

    def query_payment_status(self, order_tracking_id):
        """Query the payment status using the order tracking ID."""
        endpoint = f"Transactions/QueryPaymentStatus?orderTrackingId={order_tracking_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.authenticate()}"
        }

        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()  # Return the JSON response with payment status
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Exception: {e}")
            raise
        except Exception as e:
            logging.error(f"Error querying payment status: {e}")
            raise
    def submit_order(self, payment_data):
        endpoint = 'Transactions/SubmitOrderRequest'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.authenticate()}"
        }

        try:
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=payment_data,
                headers=headers
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            # Extract actual redirect URL from Pesapal's response
            redirect_url = data.get('call_back_url') or data.get('redirect_url')
            return {
                "redirect_url": redirect_url,
                "order_tracking_id": data.get('order_tracking_id'),
                "status": data.get('status')
            }
        except requests.exceptions.RequestException as e:
            logging.exception(f"Request Exception: {e}")
            raise  # Re-raise the exception to be handled in the route
        except (ValueError, KeyError) as e:
            logging.exception(f"JSON decode error or missing key: {e}")
            raise


    def check_transaction_status(self, tracking_id):
        endpoint = f"Transactions/GetTransactionStatus?orderTrackingId={tracking_id}"
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers={'Authorization': f"Bearer {self.authenticate()}"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.exception(f"Request Exception: {e}")
            raise

# ======== Payment Routes ========
@app.route('/initiate_payment', methods=['GET', 'POST'])
@login_required
def initiate_payment():
    try:
        # Get user and cart data
        user = User.query.get_or_404(current_user.id)
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

        if not cart_items:
            flash("Your cart is empty!", "warning")
            return redirect(url_for('view_cart'))

        # Calculate total price
        total_price = sum(
            int(Post.query.get_or_404(item.post_id).price) * item.quantity
            for item in cart_items
        )

         # Generate unique IDs and amounts
        order_id = str(uuid.uuid4())  # Unique order ID
        total_amount = round(total_price, 2)

        # Build payment payload
        payment_data = {
            "id": order_id,  # Use order_id as the ID
            "amount": total_amount,
            "currency": "KES",
            "description": f"Order from {user.username}",
            "callback_url": url_for('payment_callback', _external=True),
            "response_url": url_for('home', _external=True),
            "notification_id": "0090e9da-9801-4e45-8e16-dbfdbfb751a5",
            "billing_address": {
                "email_address": user.email,
                "phone_number": user.whatsapp or "",
                "first_name": user.username,
                "last_name": ""
            }
        }

        # Store data in session *before* redirecting
        session['order_id'] = order_id
        session['total_amount'] = total_amount

        # Process payment
        pesapal = PesaPal()
        try:
            response = pesapal.submit_order(payment_data)

            if response.get('status') == '500':
                flash("Payment processing error. Please try again.", "danger")
                return redirect(url_for('view_cart'))

            # Store the Pesapal tracking ID in the session
            session['pesapal_tracking_id'] = response['order_tracking_id']
            print(f"PAYMENT_DATA:{payment_data}")
            return redirect(response['redirect_url'])

        except Exception as e:
            flash(f"Error initializing payment: {str(e)}", "danger")
            return redirect(url_for('view_cart'))

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/payment_complete', methods=['GET'])
@login_required
def payment_complete():
    """Handle successful payment redirect from Pesapal."""
    flash("Payment completed successfully!", "success")
    return redirect(url_for('home'))

@app.route('/payment_callback', methods=['GET', 'POST'])
def payment_callback():
        try:
            # Debug: Check session contents
            current_app.logger.info(f"Session data: {session}")

            # Verify required session keys exist
            tracking_id = session.get('pesapal_tracking_id')
            order_id = session.get('order_id')
            total_amount = session.get('total_amount')

            if not all([tracking_id, order_id, total_amount]):
                current_app.logger.error("Missing session data")
                flash("Session data not found", "danger")
                return redirect(url_for('view_cart'))

            # Calculate platform fee (10% in this example)
            PLATFORM_FEE_PERCENTAGE = 0.10
            platform_fee = round(total_amount * PLATFORM_FEE_PERCENTAGE, 2)

            # Try to find existing transaction
            transaction = Transaction.query.filter_by(order_id=order_id).first()

            if not transaction:
                # Create new transaction with all required fields
                transaction = Transaction(
                    order_id=order_id,
                    tracking_id=tracking_id,
                    buyer_id=current_user.id,
                    total_amount=total_amount,
                    platform_fee=platform_fee,
                    status='pending',
                    date_created=datetime.utcnow()
                )
                db.session.add(transaction)
                db.session.commit()

            # Process payment status
            pesapal = PesaPal()
            status_response = pesapal.check_transaction_status(tracking_id)
            payment_status = status_response.get('payment_status_description', 'pending').lower()

            # Update transaction
            transaction.status = payment_status

            if payment_status == 'completed':
                if not order_id:
                    flash("Order not found", "danger")
                    return redirect(url_for('home'))

                # Redirect to receipt page
                return redirect(url_for('generate_receipt', order_id=order_id))


        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Callback error: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "Payment processing failed",
                "error": str(e)
            }), 500


@app.route('/checkout')
@login_required
def checkout():
    try:
        # Get current cart items
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

        if not cart_items:
            flash('Your cart is empty!', 'warning')
            current_app.logger.warning("Cart is empty. Redirecting to view_cart.")
            return redirect(url_for('view_cart'))

        # Calculate total price and create a unique cart signature
        total_price = sum(
            int(Post.query.get_or_404(item.post_id).price) * item.quantity
            for item in cart_items
        )
        current_app.logger.info(f"Total price calculated: {total_price}")

        # Generate a cart hash based on items and quantities
        cart_signature = "-".join([
            f"{item.post_id}:{item.quantity}" for item in sorted(cart_items, key=lambda x: x.post_id)
        ])
        cart_hash = hashlib.md5(cart_signature.encode('utf-8')).hexdigest()

        # Check if the cart is already being processed
        if 'current_tracking_id' in session and 'current_cart_signature' in session:
            if session['current_cart_signature'] == cart_hash:
                flash('Payment is already in progress. Please wait for the payment to complete or cancel the current payment.', 'info')
                return redirect(url_for('view_cart'))

        # Store tracking ID and cart signature in session to track the current payment process
        session['current_tracking_id'] = str(uuid.uuid4())  # Assign a tracking ID
        session['current_cart_signature'] = cart_hash
        session['total_amount'] = total_price  # Store total amount

        return redirect(url_for('initiate_payment'))

    except Exception as e:
        flash(f'Error during checkout: {str(e)}', 'error')
        return redirect(url_for('view_cart'))


def generate_sales_report(start_date=None, end_date=None):
    """
    Generates a sales report with transaction details.
    """
    query = Transaction.query
    if start_date:
        query = query.filter(Transaction.date_created >= start_date)
    if end_date:
        query = query.filter(Transaction.date_created <= end_date)
    transactions = query.all()

    buyer = User.query.filter(Transaction.buyer_id==current_user.id).first()

    if not transactions:
        return "No sales data found for the given date range."

    report = "Sellers' Sales\n"
    report += "============\n"
    total_revenue = 0

    for transaction in transactions:
        report += f"Order ID: {transaction.id}\n"
        report += f"Date: {transaction.date_created.strftime('%H:%M:%S')}\n"
        report += f"Buyer: {buyer.username}\n"
        report += f"Total Amount: sh.{transaction.total_amount:.2f}\n"
        report += f"Platform Fee: sh.{transaction.platform_fee:.2f}\n"
        report += "Items:\n"
        for item in transaction.items:
            post = Post.query.get(item.post_id)
            report += f"  - {post.title} (x{item.quantity}) - Price: ${item.price:.2f}\n"
        report += "---\n"
        total_revenue += transaction.total_amount

    report += f"\nTotal Revenue: ${total_revenue:.2f}\n"
    return report


@app.route('/generate_sales_report', methods=['GET'], endpoint='sales_report_route')
@login_required
def generate_sales_report_route():
    """
    Generates and returns a sales report as plain text.
    Supports date filtering via query parameters.
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Validate dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.", "error")
        return redirect(url_for('home'))

    report = generate_sales_report(start_date, end_date)
    return make_response(report, {'Content-Type': 'text/plain'})


@app.route('/receipt/<order_id>', methods=['GET'])
def generate_receipt(order_id):
    try:
        order = Transaction.query.filter_by(order_id=order_id).first()
        print(f"Order items: {order.items}")  # Verify items exist
        for item in order.items:
            print(f"Item cart_item: {item.cart_item.post.title}")  # Verify relationship works

        html = render_template('receipt.html', order=order)
        print("Rendered HTML:", html[:200])  # Check for errors

        # Create receipts folder if missing
        receipts_dir = os.path.join(app.root_path, 'receipts')
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)

        # Generate PDF
        pdf_path = os.path.join(receipts_dir, f'{order_id}.pdf')
        pdfkit.from_string(
            html,
            pdf_path,
            configuration=config,
            options={
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
        )

        # Return PDF as download
        return send_file(
            pdf_path,
            as_attachment=True,
            attachment_filename=f'receipt_{order_id}.pdf'
        )

    except Exception as e:
        logging.error(f"PDF generation error: {e}", exc_info=True)
        flash("Your generated sales report ready", "success")
        return redirect(url_for('home'))

# Then add routes for generating reports
@app.route("/seller/reports", methods=["GET"])
@login_required
def seller_reports():
    if not current_user.is_seller:  # Add this field to your User model
        abort(403)
    sales_count = TransactionItem.query.filter_by(seller_id=current_user.id).count()
    total_revenue = current_user.total_sales or 0
    available_balance = current_user.account_balance or 0

    # Get recent sales
    recent_sales = db.session.query(
        TransactionItem, Post, User
    ).join(
        Post, TransactionItem.post_id == Post.id
    ).join(
        Transaction, TransactionItem.transaction_id == Transaction.id
    ).join(
        User, Transaction.buyer_id == User.id
    ).filter(
        TransactionItem.seller_id == current_user.id
    ).order_by(
        Transaction.date_created.desc()
    ).limit(10).all()

    # Get pending disbursements
    pending_amount = db.session.query(
        db.func.sum(TransactionItem.seller_amount)
    ).filter(
        TransactionItem.seller_id == current_user.id,
        TransactionItem.is_disbursed == False
    ).scalar() or 0

    return render_template(
        'seller_dashboard.html',
        sales_count=sales_count,
        total_revenue=total_revenue,
        available_balance=available_balance,
        pending_amount=pending_amount,
        recent_sales=recent_sales
    )

# Add Jinja2 Filter to Format Currency
@app.template_filter()
def format_currency(value):
    """Format a numeric value as currency."""
    return f'{value:,.2f} KES'


# Route to trigger receipt generation
@app.route("/receipt_test", methods=["GET"])
@login_required
def generate_receipt_page():
     transaction = Transaction.query.first()  # Fetch the first transaction
     if transaction:
        html = generate_receipt(transaction)
        return html
     else:
        return "No transactions available to generate a receipt."

@app.route('/sales_report', methods=['GET'], endpoint='seller_sales_report')
@login_required
def sales_report():
    try:
        # Fetch all users who have sold products
        sellers = User.query.join(TransactionItem).filter(
            TransactionItem.seller_id == User.id
        ).distinct().all()

        # Generate sales data for each seller
        sales_data = []
        for seller in sellers:
            total_sales = TransactionItem.query.filter_by(seller_id=seller.id).with_entities(
                db.func.sum(TransactionItem.seller_amount).label('total_sales')
            ).scalar()
            sales_data.append({
                'seller': seller.username,
                'total_sales': total_sales or 0.0,
                'last_sale': TransactionItem.query.filter_by(seller_id=seller.id)
                    .order_by(TransactionItem.disbursement_date.desc())
                    .first().disbursement_date if total_sales else None
            })

        # Render the report template
        return render_template('sales_report.html', sales_data=sales_data)

    except Exception as e:
        logging.error(f"Sales report error: {e}")
        flash("Failed to generate sales report", "danger")
        return redirect(url_for('home'))
