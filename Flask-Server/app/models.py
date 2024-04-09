from . import db
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy
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


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    # Assuming profile_image_url is a URL to the user's profile image
    # Set nullable=True if you want to allow users without a profile image
    profile_image_url = db.Column(db.String(255), nullable=True)
    spotify_access_token = db.Column(db.String(255))
    spotify_refresh_token = db.Column(db.String(255))
    spotify_token_expiry = db.Column(db.DateTime)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

    


