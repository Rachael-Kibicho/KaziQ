import uuid
import requests
import json
from flask import current_app, render_template, url_for, flash, redirect, request, jsonify, abort, session
import time
from stream_chat import StreamChat
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from flaskblog import app, db, bcrypt, STREAM_API_KEY, STREAM_API_SECRET
from flaskblog.models import User, Post, CartItem, Notification, Transaction, TransactionItem, db
from flask_login import login_user, current_user, logout_user, login_required
import os
import secrets
from PIL import Image
from flask_migrate import Migrate
from datetime import datetime
from requests_oauthlib import OAuth1
import requests

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

        post = Post(title=form.title.data, content=form.content.data,price=form.price.data, author=current_user, image_file=image_file)
        db.session.add(post)
        db.session.commit()
        flash('Your Post has been created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_posts.html', title='New Post', form=form)

@app.route("/post/<int:post_id>")
@login_required
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


# Report generation routes

#Report for registered businsesses
@app.route('/report/registered_businesses')
@login_required
def registered_businesses_report():
    admin_required()  # Restrict access to admins
    users = User.query.all()
    return render_template('registered_business_report.html', users=users)

#Report for messaging activity

@app.route('/report/chat_activity')
@login_required
def chat_activity_report():
    if not current_user.is_authenticated or not current_user.is_admin:  # Restrict access to admins
        abort(403)

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
    if not current_user.is_authenticated or not current_user.is_admin:  # Restrict access to admins
        abort(403)

    # Total number of items in carts
    total_items = db.session.query(db.func.count(CartItem.id)).scalar()

    # Total number of unique users with items in their carts
    unique_users = db.session.query(CartItem.user_id).distinct().count()

    # Total quantity of items in all carts
    total_quantity = db.session.query(db.func.sum(CartItem.quantity)).scalar()

    return render_template('cart_activity_report.html', total_items=total_items, unique_users=unique_users, total_quantity=total_quantity)
class PesaPal:
    def __init__(self):
        self.base_url = "https://cybqa.pesapal.com/pesapalv3/api"
        self.token = None
        self.consumer_key = "qkio1BGGYAXTu2JOfm7XSXNruoZsrqEW"  # Move to config later
        self.consumer_secret = "osGQ364R49cXKeOYSpaOnT++rHs="  # Move to config later
        self.ipn_id = "0090e9da-9801-4e45-8e16-dbfdbfb751a5"  # Your IPN ID goes here

    def authenticate(self):
        """Handle authentication with retry logic"""
        try:
            if self.token:  # Reuse existing token if valid
                return self.token

            endpoint = "Auth/RequestToken"
            payload = {
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret
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
            print(f"Authentication Error: {str(e)}")
            self.token = None
            raise

    def submit_order(self, payment_data):
        """Submit order with mandatory IPN integration"""
        endpoint = 'Transactions/SubmitOrderRequest'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.authenticate()}"
        }

        # Add IPN configuration to payment data
        payment_data.update({
            "ipn_notification_type": "POST",  # or "GET" based on your setup
            "ipn_notification_url": "https://yourdomain.com/payment_callback",
            "ipn_id": self.ipn_id
        })

        response = requests.post(
            f"{self.base_url}/{endpoint}",
            json=payment_data,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "redirect_url": data.get('redirect_url'),
                "order_tracking_id": data.get('order_tracking_id'),
                "status": data.get('status'),
                "ipn_response": data.get('ipn_notification')  # Track IPN status
            }
        else:
            raise Exception(f"Payment failed: {response.text}")

    def check_transaction_status(self, tracking_id):
        endpoint = f"Transactions/GetTransactionStatus?orderTrackingId={tracking_id}"
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            headers={
                'Authorization': f"Bearer {self.authenticate()}",
                'Content-Type': 'application/json'
            }
        )
        response.raise_for_status()
        return response.json()

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

        # Build payment payload
        payment_data = {
            "id": str(uuid.uuid4()),  # Generate unique ID
            "amount": total_price,
            "currency": "KES",
            "description": f"Order from {user.username}",
            "callback_url": url_for('payment_callback', _external=True),
            "response_url": url_for('payment_complete', _external=True),
            "notification_id": "0090e9da-9801-4e45-8e16-dbfdbfb751a5",
            "billing_address": {
                "email_address": user.email,
                "phone_number": user.whatsapp or "",
                "first_name": user.username,
                "last_name": ""
            }
        }

        # Process payment
        pesapal = PesaPal()
        try:
            response = pesapal.submit_order(payment_data)

            if response.get('status') == '500':
                flash("Payment processing error. Please try again.", "danger")
                return redirect(url_for('view_cart'))

            return redirect(response['redirect_url'])

        except Exception as e:
            flash(f"Error initializing payment: {str(e)}", "danger")
            return redirect(url_for('view_cart'))

    except Exception as e:
        return render_template('error.html', error=str(e))



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
                transaction.completed_at = datetime.utcnow()

            db.session.commit()

            return jsonify({
                "status": "success",
                "order_id": order_id,
                "payment_status": payment_status
            })

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

        # Try to get existing order tracking ID for this cart state
        existing_tracking_id = session.get('pesapal_tracking_id')
        existing_cart_signature = session.get('cart_hash')
        current_app.logger.info(f"Existing tracking ID: {existing_tracking_id}, Existing cart signature: {existing_cart_signature}")

        # If cart has changed or no tracking ID exists, generate a new one
        if existing_cart_signature != cart_signature or not existing_tracking_id:
            try:

                # Create a unique order ID (This will be your internal reference)
                order_id = str(uuid.uuid4())
                current_app.logger.info(f"New order ID generated: {order_id}")

                # Build payment payload
                payment_data = {
                    "id": order_id,  # Generate unique ID
                    "amount": total_price,
                    "currency": "KES",
                    "description": f"Order from {current_user.username}",
                    "callback_url": url_for('payment_callback', _external=True),
                    "response_url": url_for('payment_complete', _external=True),
                    "notification_id": "0090e9da-9801-4e45-8e16-dbfdbfb751a5",
                    "billing_address": {
                        "email_address": current_user.email,
                        "phone_number": current_user.whatsapp or "",
                        "first_name": current_user.username,
                        "last_name": ""
                    }
                }
                current_app.logger.info(f"Payment data: {payment_data}")

                # Process payment
                pesapal = PesaPal()
                response = pesapal.submit_order(payment_data)
                current_app.logger.info(f"PesaPal submit_order response: {response}")

                if response.get('status') == '500':
                    flash("Payment processing error. Please try again.", "danger")
                    current_app.logger.error("PesaPal returned status 500.")
                    return redirect(url_for('view_cart'))

                # Store new tracking ID and cart signature in session
                session['pesapal_tracking_id'] = response['order_tracking_id']
                session['cart_hash'] = cart_signature
                session['order-id'] = order_id
                session['total_amount'] = total_price
                current_app.logger.info("New tracking ID and cart signature stored in session.")

                tracking_id = response['order_tracking_id']
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error during PesaPal interaction: {str(e)}")
                flash("Checkout process failed", "danger")
                return redirect(url_for('view_cart'))
        else:
            # Use existing tracking ID if cart hasn't changed
            tracking_id = existing_tracking_id
            current_app.logger.info(f"Using existing tracking ID: {tracking_id}")

        # Prepare seller information for display
        sellers_info = {}
        for item in cart_items:
            post = Post.query.get_or_404(item.post_id)
            seller = User.query.get_or_404(post.user_id)

            if seller.id not in sellers_info:
                sellers_info[seller.id] = {
                    'name': seller.username,
                    'total': 0,
                    'items': []
                }

            item_price = float(post.price) * item.quantity
            sellers_info[seller.id]['total'] += item_price
            sellers_info[seller.id]['items'].append({
                'title': post.title,
                'quantity': item.quantity,
                'price': post.price,
                'subtotal': item_price
            })

        # Render checkout template with iframe URL
        iframe_url = f"https://cybqa.pesapal.com/pesapaliframe/PesapalIframe3/Index?OrderTrackingId={tracking_id}"
        current_app.logger.info(f"Rendering checkout template with iframe URL: {iframe_url}")
        return render_template(
            'checkout.html',
            iframe_url=iframe_url,
            cart_items=cart_items,
            sellers=sellers_info,
            total_price=total_price)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in checkout: {str(e)}")
        flash("Checkout process failed", "danger")
        return redirect(url_for('view_cart'))

@app.route('/payment_complete')
@login_required
def payment_complete():
    tracking_id = session.get('pesapal_tracking_id')
    order_id = session.get('order_id')
    total_amount = session.get('total_amount')

    if not all([tracking_id, order_id, total_amount]):
        flash("Payment information not found", "danger")
        return redirect(url_for('view_cart'))

    try:
        # Verify payment status
        pesapal = PesaPal()
        status_response = pesapal.check_transaction_status(tracking_id)
        payment_status = status_response.get('payment_status_description', '').lower()

        # Process the order based on the payment status
        if status_response.get('payment_status_description') == 'Completed':
            # Get cart items
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

            # Calculate platform fee
            platform_fee = total_amount * (PLATFORM_FEE_PERCENTAGE / 100)

            # Create transaction record
            transaction = Transaction(
                order_id=order_id,
                tracking_id=tracking_id,
                buyer_id=current_user.id,
                total_amount=total_amount,
                platform_fee=platform_fee,
                status='completed'
            )
            db.session.add(transaction)
            db.session.flush()  # Get the transaction ID without committing

            # Create transaction items and update seller balances
            for cart_item in cart_items:
                post = Post.query.get_or_404(cart_item.post_id)
                seller = User.query.get_or_404(post.user_id)

                # Calculate amounts
                item_total = float(post.price) * cart_item.quantity
                seller_amount = item_total * (1 - PLATFORM_FEE_PERCENTAGE / 100)

                # Create transaction item
                transaction_item = TransactionItem(
                    transaction_id=transaction.id,
                    post_id=post.post_id,
                    seller_id=seller.id,
                    quantity=cart_item.quantity,
                    price=float(post.price),
                    seller_amount=seller_amount
                )
                db.session.add(transaction_item)

                # Update seller statistics
                seller.account_balance += seller_amount
                seller.total_sales += item_total
            # Clear the cart after successful payment
            CartItem.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()

            # Clear session tracking data
            session.pop('pesapal_tracking_id', None)
            session.pop('cart_hash', None)
            session.pop('order_id', None)
            session.pop('total_amount', None)

            flash("Payment successful! Your order has been processed.", "success")
            return redirect(url_for('home'))
        else:
            flash(f"Payment status: {status_response.get('payment_status_description')}", "info")
            return redirect(url_for('view_cart'))

    except Exception as e:
        flash(f"Error checking payment status: {str(e)}", "danger")
        return redirect(url_for('view_cart'))

@app.route('/order_confirmation/<order_id>')
@login_required
def order_confirmation(order_id):
    transaction = Transaction.query.filter_by(order_id=order_id, buyer_id=current_user.id).first_or_404()
    items = TransactionItem.query.filter_by(transaction_id=transaction.id).all()

    return render_template(
        'order_confirmation.html',
        transaction=transaction,
        items=items
    )
