from flask import Blueprint, g, render_template, redirect, url_for, session, request, flash
from .models import User, UserOAuth
from .forms import LoginForm, RegistrationForm  # Import your forms
from .utils import allowed_file  # Import utility functions
from . import db
from werkzeug.utils import secure_filename
from spotipy.oauth2 import SpotifyOAuth  # Import SpotifyOAuth
import os
import spotipy
from flask import current_app

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}




# Routes
@main.route('/')
def index():
    return render_template('index.html')


@main.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    print("Current app name:", current_app.name)  # Debug statement
    print("DB:", db)  # Debug statement
    if form.validate_on_submit():
        # Save profile image if it's included
        if form.profile_image.data:
            file = form.profile_image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)

                file_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], filename)                # Make sure the path is relative to the Flask app
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
        return redirect(url_for('main.dash'))
    return render_template('register.html', form=form)

@main.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'user_id' in session:
        return redirect(url_for('index'))  # or dashboard if already logged in
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('main.signin'))
        session['user_id'] = user.id
        return redirect(url_for('main.index'))
    return render_template('signin.html', form=form)

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@main.route('/dash')
def dash():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None

        if user is None:
            # Handle case where user not found
            return redirect(url_for('main.logout'))

        # Pass the spotify_connected variable to the template
        return render_template('dash.html', user=user, spotify_connected=spotify_connected)
    return redirect(url_for('main.signin'))



@main.route('/connect_spotify')
def connect_spotify():
    if 'user_id' not in session:
        flash('You must be logged in to connect your Spotify account.')
        return redirect(url_for('main.signin'))

    scope = 'user-read-private user-read-email user-top-read user-read-recently-played'
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
    auth_url = oauth_manager.get_authorize_url()
    return redirect(auth_url)

@main.route('/spotify_callback')
def spotify_callback():
    if 'user_id' not in session:
        return redirect(url_for('main.signin'))

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
            return redirect(url_for('main.dash'))
        else:
            flash("Invalid token data received from Spotify. Please try again.")
            return redirect(url_for('connect_spotify'))
    else:
        return "Authorization failed with Spotify", 400
    

@main.route('/spotify_insights')
def spotify_insights():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None
        
        if not user_oauth or not user_oauth.spotify_access_token:
            return redirect(url_for('connect_spotify'))

        oauth_manager = SpotifyOAuth(cache_path=session_cache_path(session['user_id']))
        spotify = spotipy.Spotify(auth_manager=oauth_manager)
        user_data = spotify.current_user()

        followers = user_data['followers']['total']
        # ... Fetch more data as needed ...

        # Assuming you've added the necessary data to spotify_data dictionary
        spotify_data = {
            'followers': followers,
            # ... other Spotify data ...
        }

        return render_template('spotify_insights.html', user=user, spotify_data=spotify_data,spotify_connected=spotify_connected)
    return redirect(url_for('main.signin'))




@main.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        # Adjusting the query method to align with SQLAlchemy 2.0 guidelines
        g.user = db.session.query(User).get(user_id)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def session_cache_path(user_id):
    return ".cache-" + str(user_id)
