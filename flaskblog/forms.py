from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, StringField, PasswordField, SubmitField, BooleanField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from flaskblog.models import User, Post, CATEGORIES
from flask_login import current_user

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

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    whatsapp = StringField('Whatsapp Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken, please choose another one')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already taken, please choose another one')

    def validate_whatsapp(self, whatsapp):
        user = User.query.filter_by(whatsapp=whatsapp.data).first()
        if user:
            raise ValidationError('Whatsapp number already registered')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    whatsapp = StringField('Whatsapp Number', validators=[DataRequired(), Length(min=10, max=15)])
    bank_account = StringField('Bank Account Number', validators=[Optional(), Length(max=50)])
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    phone_for_payment = StringField('Mobile Money Number', validators=[Optional(), Length(max=20)])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already taken, please choose another one')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already taken, please choose another one')

    def validate_whatsapp(self, whatsapp):
        if whatsapp.data != current_user.whatsapp:
            user = User.query.filter_by(whatsapp=whatsapp.data).first()
            if user:
                raise ValidationError('Whatsapp number already registered')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    price = StringField('Price', validators=[DataRequired()])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired()])
    image = FileField('Upload Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Post')

class PaymentSettingsForm(FlaskForm):
    bank_account = StringField('Bank Account Number', validators=[DataRequired(), Length(max=50)])
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    phone_for_payment = StringField('Mobile Money Number', validators=[DataRequired(), Length(max=20)])
    submit = SubmitField('Save Payment Settings')

class UpdatePostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    price = StringField('Price', validators=[DataRequired()])
    category = SelectField('Category', choices=CATEGORIES, validators=[DataRequired()])
    image = FileField('Upload Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Post')
