import requests
from datetime import datetime, timedelta

# Assuming you have the correct import paths for your project
from .models import User
from . import db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

import requests
from base64 import b64encode
from .routes import db

def refresh_spotify_token(user):
    """
    Refreshes the Spotify access token for the given user.
    :param user: User instance for which to refresh the token.
    """
    client_id = 'YOUR_SPOTIFY_CLIENT_ID'
    client_secret = 'YOUR_SPOTIFY_CLIENT_SECRET'
    refresh_token = user.spotify_refresh_token

    # Encode the client ID and secret for the header
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = b64encode(client_creds.encode()).decode()

    # Spotify token endpoint
    token_url = "https://accounts.spotify.com/api/token"
    
    # Request headers and data
    headers = {"Authorization": f"Basic {client_creds_b64}"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    # Make the POST request to refresh the token
    response = requests.post(token_url, headers=headers, data=data)

    # Check if the request was successful
    if response.status_code == 200:
        token_info = response.json()
        user.spotify_access_token = token_info.get('access_token')

        # Optionally, update the refresh token if a new one is provided
        if 'refresh_token' in token_info:
            user.spotify_refresh_token = token_info['refresh_token']

        # Update the token expiry time
        # Spotify tokens typically expire in 3600 seconds (1 hour)
        user.spotify_token_expiry = datetime.now() + timedelta(seconds=token_info.get('expires_in', 3600))

        # Save the updated user info to your database
        db.session.commit()
    else:
        # Handle error cases (e.g., log the error, notify an administrator)
        print(f"Failed to refresh Spotify token: {response.text}")

def fetch_spotify_playlists(user):
    if user.spotify_token_expiry <= datetime.now():
        refresh_spotify_token(user)
    headers = {"Authorization": f"Bearer {user.spotify_access_token}"}
    response = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None
