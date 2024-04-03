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



import os
from flask import Flask, redirect, url_for, session, request, flash
from spotipy.oauth2 import SpotifyOAuth

# Now you can safely load environment variables
sp_client_id = os.environ.get('SPOTIPY_CLIENT_ID')
sp_client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')
sp_redirect_uri = os.environ.get('SPOTIPY_REDIRECT_URI')

print("SPOTIPY_CLIENT_ID:", sp_client_id)
print("SPOTIPY_CLIENT_SECRET:", sp_client_secret)
print("SPOTIPY_REDIRECT_URI:", sp_redirect_uri)

spotify_oauth = SpotifyOAuth(client_id=sp_client_id,
                             client_secret=sp_client_secret,
                             redirect_uri=sp_redirect_uri,
                             scope="user-library-read")
# Rest of your Flask application code follows...



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
    spotify_key = db.Column(db.String(255), nullable=True)
    youtube_key = db.Column(db.String(255), nullable=True)  # Add this line for YouTube Music

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
    spotify_token = db.Column(db.String(2048), nullable=True)
    youtube_token = db.Column(db.String(2048), nullable=True)

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
        if user is None:
            # Handle case where user not found
            return redirect(url_for('logout'))

        # Check if Spotify and YouTube Music are connected
        spotify_connected = user.spotify_key is not None
        youtube_connected = user.youtube_key is not None

        return render_template('dash.html', user=user, spotify_connected=spotify_connected, youtube_connected=youtube_connected)
    return redirect(url_for('signin'))



@app.route('/connect_spotify')
def connect_spotify():
    spotify_oauth = SpotifyOAuth(
        client_id='your_spotify_client_id',
        client_secret='your_spotify_client_secret',
        redirect_uri=url_for('spotify_callback', _external=True),
        scope='user-library-read user-read-email'
    )
    auth_url = spotify_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/connect_spotify_callback')
def spotify_callback():
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Error during Spotify login: {error}')
        return redirect(url_for('index'))

    if code:
        spotify_oauth = get_spotify_oauth()  # Ensure you're initializing SpotifyOAuth here if not globally
        token_info = spotify_oauth.get_access_token(code)
        if token_info:
            # Here, you might want to save token_info in the session or a database
            session['token_info'] = token_info  # Example: Storing the token in the user session
            flash("Spotify connected successfully.")
            return redirect(url_for('dash'))
        else:
            flash("Failed to get the access token from Spotify.")
            return redirect(url_for('index'))
    else:
        flash("No code provided by Spotify.")
        return redirect(url_for('index'))

def create_youtube_oauth_flow():
    return Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=['https://www.googleapis.com/auth/youtube.readonly'],
        redirect_uri=url_for('youtube_callback', _external=True)
    )

# @app.route('/connect_youtube')
# def connect_youtube():
#     flow = create_youtube_oauth_flow()
#     auth_url, state = flow.authorization_url(prompt='consent', include_granted_scopes='true')
#     session['state'] = state  # Save 'state' in the session or database for validation
#     return redirect(auth_url)

# @app.route('/connect_youtube_callback')
# def youtube_callback():
#     flow = create_youtube_oauth_flow()
#     flow.fetch_token(authorization_response=request.url)
#     credentials = flow.credentials

#     # Store credentials in the database associated with the current user
#     user_id = session.get('user_id')
#     save_youtube_credentials(user_id, credentials.to_json())

#     return redirect(url_for('dash'))


def save_spotify_credentials(user_id, token_info):
    # Find existing OAuth entry or create a new one
    oauth_credentials = UserOAuth.query.filter_by(user_id=user_id).first()
    if not oauth_credentials:
        oauth_credentials = UserOAuth(user_id=user_id)
        db.session.add(oauth_credentials)
    
    # Update Spotify token
    oauth_credentials.spotify_token = token_info  # Assuming you're storing the entire token JSON as a string
    db.session.commit()

    from flask import current_app, session, url_for
from spotipy.oauth2 import SpotifyOAuth
import os

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        scope="user-library-read",
    )



# def save_youtube_credentials(user_id, credentials_json):
#     # Find existing OAuth entry or create a new one
#     oauth_credentials = UserOAuth.query.filter_by(user_id=user_id).first()
#     if not oauth_credentials:
#         oauth_credentials = UserOAuth(user_id=user_id)
#         db.session.add(oauth_credentials)
    
#     # Update YouTube token
#     oauth_credentials.youtube_token = credentials_json  # Storing the entire credentials JSON
#     db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will now work because it's inside an application context
    app.run(debug=True)
