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
from flask import Flask, request, render_template, session, redirect, url_for
from flask_login import login_required, current_user
from .utils import fetch_spotify_playlists

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

@main.route('/spotify/playlists')
@login_required
def spotify_playlists():
    user = current_user
    playlists = fetch_spotify_playlists(user)
    if playlists:
        return render_template('playlists.html', playlists=playlists['items'])
    else:
        return "Failed to fetch playlists", 400