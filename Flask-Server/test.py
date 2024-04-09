from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserOAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_access_token = db.Column(db.String(2048))
    spotify_refresh_token = db.Column(db.String(2048))
    user = db.relationship('User', backref='oauth', uselist=False)

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash('Login successful.')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/connect_spotify')
def connect_spotify():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.')
        return redirect(url_for('login'))
    oauth_manager = SpotifyOAuth(client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                                 client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                                 redirect_uri=url_for('spotify_callback', _external=True),
                                 scope='playlist-read-private',
                                 cache_path=f".cache-{session['user_id']}")
    auth_url = oauth_manager.get_authorize_url()
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    oauth_manager = SpotifyOAuth(cache_path=f".cache-{session['user_id']}")
    code = request.args.get('code')
    token_info = oauth_manager.get_access_token(code)
    if token_info:
        user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
        if not user_oauth:
            user_oauth = UserOAuth(user_id=session['user_id'])
            db.session.add(user_oauth)
        user_oauth.spotify_access_token = token_info['access_token']
        user_oauth.spotify_refresh_token = token_info['refresh_token']
        db.session.commit()
        flash('Spotify account connected.')
    else:
        flash('Failed to retrieve access token.')
    return redirect(url_for('index'))

@app.route('/view_playlists')
def view_playlists():
    if 'user_id' not in session:
        flash('You must be logged in to view this page.')
        return redirect(url_for('login'))
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        flash("Spotify account not connected.")
        return redirect(url_for('connect_spotify'))
    spotify = spotipy.Spotify(auth=user_oauth.spotify_access_token)
    playlists = spotify.current_user_playlists()
    return render_template('playlists.html', playlists=playlists['items'])

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
