from flask import Flask, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField
from wtforms.validators import DataRequired, Email, EqualTo
from flask import Flask, render_template, redirect, url_for, flash, session, g
from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField
from wtforms.validators import DataRequired, Email, EqualTo
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask import Flask, redirect, url_for, session
from spotipy.oauth2 import SpotifyOAuth
import os
from flask import Flask, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from flask import session, redirect, url_for
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
load_dotenv()  # This loads the variables from .env into the environment
import spotipy
from spotipy.oauth2 import SpotifyOAuth



import os
from flask import Flask, redirect, url_for, session, request, flash
from spotipy.oauth2 import SpotifyOAuth



# Now you can safely load environment variables



# Load your Google OAuth2.0 Client Secrets file



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///musiclang.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads/profile_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    # Assuming profile_image_url is a URL to the user's profile image
    # Set nullable=True if you want to allow users without a profile image
    profile_image_url = db.Column(db.String(255), nullable=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

    

# Forms
class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    profile_image = FileField('Profile Image', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UserOAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_access_token = db.Column(db.String(2048), nullable=True)
    spotify_refresh_token = db.Column(db.String(2048), nullable=True)

    user = db.relationship('User', backref=db.backref('oauth_credentials', lazy=True))


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Save profile image if it's included
        if form.profile_image.data:
            file = form.profile_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Make sure the path is relative to the Flask app
                file_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                # Correctly reference the saved file for web access
                profile_image_url = url_for('static', filename=os.path.join('uploads/profile_images', filename))
            else:
                flash('Invalid file type.')
                return redirect(request.url)
        else:
            profile_image_url = None  # Or set a default image path

        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            profile_image_url=profile_image_url
            # Other fields...
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user and logged in!')
        return redirect(url_for('dash'))
    return render_template('register.html', form=form)




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'user_id' in session:
        return redirect(url_for('index'))  # or dashboard if already logged in
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('signin'))
        session['user_id'] = user.id
        return redirect(url_for('index'))
    return render_template('signin.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/dash')
def dash():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None

        if user is None:
            # Handle case where user not found
            return redirect(url_for('logout'))

        # Pass the spotify_connected variable to the template
        return render_template('dash.html', user=user, spotify_connected=spotify_connected)
    return redirect(url_for('signin'))



def session_cache_path(user_id):
    return ".cache-" + str(user_id)


@app.route('/connect_spotify')
def connect_spotify():
    if 'user_id' not in session:
        flash('You must be logged in to connect your Spotify account.')
        return redirect(url_for('signin'))

    scope = 'user-read-private user-read-email user-top-read user-read-recently-played'
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
    auth_url = oauth_manager.get_authorize_url()
    return redirect(auth_url)



@app.route('/spotify_callback')
def spotify_callback():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    oauth = SpotifyOAuth(cache_path=session_cache_path(session['user_id']))
    if not oauth:
        flash("Spotify OAuth setup failed. Please try again.")
        return redirect(url_for('connect_spotify'))

    # Check if we have received the "code" query parameter from Spotify's redirect
    if request.args.get("code"):
        token_info = oauth.get_access_token(request.args["code"])
        if not token_info:
            flash("Failed to retrieve access token. Please try connecting again.")
            return redirect(url_for('connect_spotify'))

        user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
        if not user_oauth:
            user_oauth = UserOAuth(user_id=session['user_id'])
            db.session.add(user_oauth)

        # Ensure we have a valid token before proceeding
        if 'access_token' in token_info and 'refresh_token' in token_info:
            user_oauth.spotify_access_token = token_info['access_token']
            user_oauth.spotify_refresh_token = token_info['refresh_token']
            db.session.commit()
            return redirect(url_for('dash'))
        else:
            flash("Invalid token data received from Spotify. Please try again.")
            return redirect(url_for('connect_spotify'))
    else:
        return "Authorization failed with Spotify", 400

# Assuming you have set your app's SECRET_KEY and database configurations

@app.route('/spotify_insights')
def spotify_insights():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None

        if not spotify_connected:
            return redirect(url_for('connect_spotify'))

        spotify = spotipy.Spotify(auth=user_oauth.spotify_access_token)
        user_data = spotify.current_user()
        followers = user_data['followers']['total']
        # ... Fetch more data as needed ...

        # Assuming you've added the necessary data to spotify_data dictionary
        spotify_data = {
            'followers': followers,
            # ... other Spotify data ...
        }

        return render_template('spotify_insights.html', user=user, spotify_data=spotify_data,spotify_connected=spotify_connected)
    return redirect(url_for('signin'))






@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        # Adjusting the query method to align with SQLAlchemy 2.0 guidelines
        g.user = db.session.query(User).get(user_id)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will now work because it's inside an application context
    app.run(debug=True)
