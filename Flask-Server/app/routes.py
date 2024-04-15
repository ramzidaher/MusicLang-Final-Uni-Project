# routes.py
import json
import os
from collections import Counter

from flask import (
    Blueprint, flash, g, jsonify, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.utils import secure_filename

import plotly
import plotly.express as px
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from textblob import TextBlob

from . import db
from .forms import LoginForm, RegistrationForm
from .helpers import session_cache_path
from .models import User, UserOAuth
from .utils import (
    allowed_file, aggregate_results_from_text, batch_add_tracks, fetch_lyrics,
    get_genius_client, get_language_name, get_playlist_count, predict_languages_for_line
)


main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

#Main Route
@main.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    else:
        return render_template('index.html')

@main.before_request
def load_logged_in_user():
    """
    Load the currently logged-in user into the global `g` object.

    If there is a user_id stored in the session, retrieve the corresponding user object
    from the database and assign it to `g.user`. If there's no user_id in the session,
    set `g.user` to None.

    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)


@main.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user.

    This route handles both GET and POST requests. If it's a GET request, it renders
    the registration form template. If it's a POST request, it validates the submitted
    form data. If the form is valid, it saves the user's data into the database,
    including the profile image if provided, then redirects the user to the dashboard.
    If the form is not valid, it renders the registration form template again with
    appropriate error messages.

    Args:
        None

    Returns:
        str: Renders the registration template with the registration form if it's a GET request.
        str: Redirects the user to the dashboard if registration is successful (POST request).
        str: Renders the registration template with the form and appropriate error messages if the form is not valid (POST request).

    """
        
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
        return redirect(url_for('main.dashboard'))
    return render_template('register.html', form=form)


@main.route('/signin', methods=['GET', 'POST'])
def signin():
    """
    Sign in a user.

    This route handles both GET and POST requests. If it's a GET request, it renders
    the sign-in form template. If it's a POST request, it validates the submitted
    form data. If the form is valid, it checks if the user exists in the database and
    if the provided password matches. If the credentials are valid, it sets the 'user_id'
    in the session and redirects the user to the dashboard. If the credentials are invalid,
    it renders the sign-in form template again with appropriate error messages.

    Args:
        None

    Returns:
        str: Redirects the user to the dashboard page if already logged in.
        str: Renders the sign-in template with the sign-in form if it's a GET request.
        str: Redirects the user to the dashboard upon successful sign-in (POST request).
        str: Renders the sign-in template with appropriate error messages if the sign-in fails (POST request).

    """
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))  # or dashboardboard if already logged in
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('main.signin'))
        session['user_id'] = user.id
        return redirect(url_for('main.dashboard'))
    return render_template('signin.html', form=form)


@main.route('/logout')
def logout():
    """
    Log out the current user.

    This route removes the 'user_id' from the session, effectively logging out the user,
    and redirects them to the index page.

    Args:
        None

    Returns:
        str: Redirects the user to the index page after successfully logging out.

    """
    session.pop('user_id', None)
    return redirect(url_for('main.index'))


@main.route('/dashboard')
def dashboard():
    """
    Display the user's dashboard.

    This route checks if the user is logged in by verifying the presence of 'user_id' in the session.
    If the user is logged in, it retrieves the user object from the database based on the user_id
    stored in the session. It also checks if the user has connected their Spotify account.
    If the user is not found in the database, it redirects the user to log out.
    Finally, it renders the dashboard template with the user's information and whether their Spotify
    account is connected.

    Args:
        None

    Returns:
        str: Redirects the user to the sign-in page if not logged in.
        str: Redirects the user to the logout page if the user is not found in the database.
        str: Renders the dashboard template with the user's information if logged in.

    """
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        else:
            # Handle the case where user is not found
            return redirect(url_for('main.logout'))  # or any other appropriate action
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None

        if user is None:
            # Handle case where user not found
            return redirect(url_for('main.logout'))

        # Pass the spotify_connected variable to the template
        return render_template('dashboard.html', user=user, spotify_connected=spotify_connected)
    return redirect(url_for('main.signin'))


@main.route('/connect_spotify')
def connect_spotify():
    """
    Connect Spotify account.

    This route checks if the user is logged in. If not, it flashes a message
    prompting the user to log in and redirects to the sign-in page. If the user
    is logged in, it sets the required scopes for accessing Spotify data, initializes
    the SpotifyOAuth manager with the specified scope and cache path, and redirects
    the user to the Spotify authorization URL.

    Args:
        None

    Returns:
        str: Redirects the user to the Spotify authorization URL.

    """

    # Check if user is logged in
    if 'user_id' not in session:
        # Flash message indicating that the user must be logged in
        flash('You must be logged in to connect your Spotify account.')
        # Redirect user to the sign-in page
        return redirect(url_for('main.signin'))
    # Define the required scope for Spotify access
    scope = "playlist-modify-public playlist-modify-private user-read-private user-read-email"
    # Initialize SpotifyOAuth manager with the specified scope and cache path
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
    # Get the Spotify authorization URL
    auth_url = oauth_manager.get_authorize_url()
    # Redirect user to the Spotify authorization URL
    return redirect(auth_url)


@main.route('/spotify_callback')
def spotify_callback():
    """
    Handle the callback from Spotify OAuth.

    This route verifies that the user is logged in by checking for the 'user_id' in the session.
    If the user is not logged in, it redirects them to the sign-in page.
    It then proceeds with the Spotify OAuth process, attempting to retrieve access and refresh tokens.
    If successful, it updates the user's OAuth information in the database and redirects them to the dashboard.
    If the process encounters any errors or failures, appropriate flash messages are displayed, and the user
    is redirected to retry the Spotify connection.

    Args:
        None

    Returns:
        str: Redirects the user to the sign-in page if not logged in.
        str: Redirects the user to the dashboard upon successful Spotify OAuth authentication.
        str: Redirects the user to retry the Spotify connection if an error occurs during OAuth.
        str: Displays an error message if the authorization fails with Spotify.

    """
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
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid token data received from Spotify. Please try again.")
            return redirect(url_for('connect_spotify'))
    else:
        return "Authorization failed with Spotify", 400
    

@main.route('/spotify_insights')
def spotify_insights():
    """
    Retrieve and display insights about the user's Spotify account.

    This route checks if the user is logged in by verifying the presence of 'user_id' in the session.
    If the user is logged in, it retrieves the user object from the database based on the user_id
    stored in the session. It then checks if the user has connected their Spotify account and if
    there's an access token available. If the user has not connected their Spotify account or
    there's no access token available, it redirects the user to connect their Spotify account.
    It then uses the Spotify access token to retrieve user data, such as follower count and playlist count,
    and renders a template displaying these insights.

    Args:
        None

    Returns:
        str: Redirects the user to the connect_spotify route if not connected to Spotify.
        str: Redirects the user to the sign-in page if not logged in.
        str: Renders the Spotify insights template with user and Spotify data if logged in and connected to Spotify.

    """
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_oauth = UserOAuth.query.filter_by(user_id=user.id).first()
        spotify_connected = user_oauth and user_oauth.spotify_access_token is not None
        
        if not user_oauth or not user_oauth.spotify_access_token:
            return redirect(url_for('main.connect_spotify'))

        oauth_manager = SpotifyOAuth(cache_path=session_cache_path(session['user_id']))
        spotify = spotipy.Spotify(auth_manager=oauth_manager)
        user_data = spotify.current_user()
        
        # Get playlist count
        playlist_count = get_playlist_count(spotify)
        
        followers = user_data['followers']['total']
        
        # Extend spotify_data with the playlist count
        spotify_data = {
            'followers': followers,
            'playlist_count': playlist_count,
            # Add other Spotify data as needed
        }

        return render_template('spotify_insights.html', user=user, spotify_data=spotify_data, spotify_connected=spotify_connected)
    else:
        return redirect(url_for('main.signin'))


@main.route('/feature_analyze', methods=['GET', 'POST'])
def feature_analyze():
    """
    Perform analysis on Spotify playlists.

    This route handles both GET and POST requests. If it's a GET request without
    any parameters, it checks if the user is logged in. If not, it redirects the
    user to the sign-in page. If the user is logged in, it fetches the user's
    playlists for potential analysis.

    If a playlist_id and 'analyze' parameter set to 'true' are provided in the
    request, it performs analysis on the specified playlist and displays the results.

    If only a playlist_id is provided, it displays the tracks of the specified playlist
    for potential analysis.

    Args:
        None

    Returns:
        str: Redirects the user to the sign-in page if not logged in.
        str: Renders the page with the user's playlists for potential analysis.
        str: Displays the analysis results for the specified playlist if analysis is requested.
        str: Displays the tracks of the specified playlist for potential analysis.

    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main.signin'))

    playlist_id = request.args.get('playlist_id')
    analyze = request.args.get('analyze', 'false') == 'true'  # Check if analysis is requested

    if playlist_id and analyze:
        # Perform analysis and display results
        return analyze_playlist_languages(playlist_id)
    else:
        # Initial page load, show user playlists
        return fetch_user_playlists(user_id)


def fetch_user_playlists(user_id):
    """
    Fetch playlists for the specified user from Spotify, excluding liked songs.

    This function retrieves the user's playlists from Spotify using the user's
    OAuth token. If the user has connected their Spotify account and there's
    an access token available, it fetches the playlists and renders a template
    displaying them. Liked songs are excluded from the playlists shown.

    Args:
        user_id (int): The ID of the user whose playlists are to be fetched.

    Returns:
        str: Renders the page with the user's playlists for potential analysis.
        str: Redirects the user to the dashboard if not connected to Spotify.
    """
    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if user_oauth and user_oauth.spotify_access_token:
        oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
        spotify = spotipy.Spotify(auth_manager=oauth_manager)
        results = spotify.current_user_playlists(limit=50)
        
        # This will result in only actual playlists being displayed
        playlists = [{'name': playlist['name'], 'id': playlist['id']} for playlist in results['items']]
                    
        return render_template('feature_analyze.html', playlists=playlists, user=g.user)
    else:
        flash('Please connect to Spotify.', 'info')
        return redirect(url_for('main.dashboard'))


@main.route('/api/playlist_tracks/<playlist_id>')
def api_playlist_tracks(playlist_id):
    if 'user_id' not in session:
        return {'error': 'User not logged in'}, 403

    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return {'error': 'Spotify not connected'}, 403

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
    tracks = []

    if playlist_id == 'saved_tracks':
        # Fetch user's saved tracks
        results = spotify.current_user_saved_tracks(limit=50)
        while results:
            tracks.extend([{'name': item['track']['name'],
                            'artist': ', '.join(artist['name'] for artist in item['track']['artists'])}
                           for item in results['items'] if item['track']])
            results = spotify.next(results)  # Move to the next page of saved tracks

    else:
        # Fetch tracks from a specific playlist
        results = spotify.playlist_tracks(playlist_id, limit=100)
        while results:
            tracks.extend([{'name': item['track']['name'],
                            'artist': ', '.join(artist['name'] for artist in item['track']['artists'])}
                           for item in results['items'] if item['track']])
            results = spotify.next(results)  # Move to the next page of playlist tracks
    
    
    print(f"Total tracks fetched: {len(tracks)}")  # Add this line in your api_playlist_tracks function before returning the response.
    return jsonify({'tracks': tracks})


@main.before_request
def load_logged_in_user():
    """
    Load the currently logged-in user into the global context 'g'.

    This function is executed before each request. It checks if there is a user
    ID stored in the session. If found, it retrieves the corresponding user
    object from the database and stores it in the global context 'g'. If no user
    ID is found, 'g.user' is set to None.

    Notes:
        This function relies on the Flask 'session' object to retrieve the user ID
        stored during login. It also assumes that the 'User' model is available
        and imported correctly from your application's models. Additionally, it
        uses SQLAlchemy to query the database for the user object.


    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        # Adjusting the query method to align with SQLAlchemy 2.0 guidelines
        g.user = db.session.query(User).get(user_id)


@main.route('/api/lyrics')
def get_lyrics():
    """
    Retrieve lyrics for a given artist and title.

    This endpoint allows users to retrieve lyrics for a specific song
    by providing the artist's name and the song's title as query parameters.

    Args:
        artist (str): The name of the artist.
        title (str): The title of the song.

    Returns:
        dict: A dictionary containing the lyrics of the requested song under the key 'lyrics'.

    Raises:
        404: If lyrics for the specified song are not found.

    """
    artist = request.args.get('artist')
    title = request.args.get('title')
    lyrics = fetch_lyrics(artist, title)

    if lyrics:
        return jsonify({"lyrics": lyrics})
    else:
        return jsonify({"error": "Lyrics not found"}), 404


@main.route('/reauthenticate_spotify')
def reauthenticate_spotify():
    """
    Reauthenticate Spotify account.

    This route checks if the user is logged in. If not, it flashes a message
    prompting the user to log in and redirects to the sign-in page. If the user
    is logged in, it sets the required scopes for accessing Spotify data, initializes
    the SpotifyOAuth manager with the specified scope and cache path, and redirects
    the user to the Spotify authorization URL for reauthentication.

    Args:
        None

    Returns:
        str: Redirects the user to the Spotify authorization URL for reauthentication.

    """

    # Check if user is logged in
    if 'user_id' not in session:
        # Flash message indicating that the user must be logged in
        flash('You must be logged in to reconnect your Spotify account.')

        # Redirect user to the sign-in page
        return redirect(url_for('main.signin'))

    # Define the required scope for Spotify reauthentication
    scope = "playlist-modify-public playlist-modify-private user-read-private user-read-email"

    # Initialize SpotifyOAuth manager with the specified scope and cache path
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))

    # Get the Spotify reauthentication authorization URL
    auth_url = oauth_manager.get_authorize_url()

    # Redirect user to the Spotify reauthentication authorization URL
    return redirect(auth_url)


@main.route('/api/all_saved_tracks')
def all_saved_tracks():
    """
    Retrieve all saved tracks from the user's Spotify account.

    This function fetches all saved tracks from the user's Spotify account.
    It first checks if the user is logged in and has connected their Spotify account.
    If not, it returns an error message with status code 403 (Forbidden).
    Otherwise, it retrieves the saved tracks using the Spotify API and returns
    them in JSON format.

    Args:
        None

    Returns:
        dict: A dictionary containing the retrieved tracks in JSON format.

    """
    # Check if user is logged in and has connected their Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session.get('user_id')).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        # Return error message if Spotify connection is required
        return jsonify({'error': 'Spotify connection is required.'}), 403
    # Initialize Spotify API client with user's OAuth token
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
    # Initialize an empty list to store tracks
    tracks = []
    # Fetch all saved tracks from the user's Spotify account
    results = spotify.current_user_saved_tracks()
    while results:
        try:
            # Extract track information and append to tracks list
            tracks.extend([{
                'name': item['track']['name'],
                'artist': item['track']['artists'][0]['name']
            } for item in results['items'] if item['track']])

            # Check for more pages
            if results['next']:
                results = spotify.next(results)
            else:
                results = None
        except Exception as e:
            # Log error if fetching tracks fails
            print("Failed to fetch tracks:", str(e))
            break
    # Return tracks in JSON format
    return jsonify({'tracks': tracks})


@main.route('/analyze_playlist_languages_stats/<playlist_id>')
def analyze_playlist_languages_stats(playlist_id):
    """
    Analyze playlist languages statistics.

    This route analyzes the languages of tracks in a Spotify playlist and returns
    statistics about the languages used in the playlist. It requires the user to
    be signed in and have a connected Spotify account. It retrieves lyrics for
    each track in the playlist, analyzes them to determine the languages used,
    and calculates statistics such as the number of tracks analyzed and the
    average percentage of each language used in the playlist.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.

    Returns:
        dict: A dictionary containing analysis results, including information
              about each track, the number of tracks analyzed, and average
              percentages of languages used in the playlist.
    """

    # Check if user is signed in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize SpotifyOAuth manager and Spotify API client
    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)

    # Initialize variables
    lyrics_and_languages = []
    num_tracks_analyzed = 0
    language_totals = {}

    # Function to process tracks
    def process_tracks(tracks):
        nonlocal num_tracks_analyzed, lyrics_and_languages, language_totals
        for item in tracks['items']:
            track_name = item['track']['name']
            artist_name = item['track']['artists'][0]['name']
            lyrics = fetch_lyrics(artist_name, track_name)  # Fetch lyrics for the track
            if lyrics:
                language_results = aggregate_results_from_text(lyrics)  # Analyze lyrics to determine languages used
                sorted_languages = sorted(language_results.items(), key=lambda x: x[1], reverse=True)
                lyrics_and_languages.append({
                    'track_name': track_name,
                    'artist_name': artist_name,
                    'languages': sorted_languages
                })
                num_tracks_analyzed += 1
                for lang, percentage in language_results.items():
                    if lang in language_totals:
                        language_totals[lang] += percentage
                    else:
                        language_totals[lang] = percentage

    # Fetch and process tracks
    try:
        if playlist_id == 'saved_tracks':
            results = spotify.current_user_saved_tracks(limit=50)
        else:
            results = spotify.playlist_tracks(playlist_id, limit=100)

        while results:
            process_tracks(results)
            if results['next']:
                results = spotify.next(results)
            else:
                results = None
    except spotipy.exceptions.SpotifyException as e:
        return jsonify({'error': f'Spotify API error: {e}'}), 400

    # Calculate average language percentages
    average_language_percentages = {}
    if num_tracks_analyzed > 0:
        average_language_percentages = {lang: (total / num_tracks_analyzed) for lang, total in language_totals.items()}
        sorted_average_languages = sorted(average_language_percentages.items(), key=lambda x: x[1], reverse=True)

    # Prepare the response
    return jsonify({
        'analysis_results': lyrics_and_languages,
        'num_tracks_analyzed': num_tracks_analyzed,
        'average_languages': {lang: percentage for lang, percentage in sorted_average_languages}
    })


@main.route('/analyze_playlist_languages/<playlist_id>')
def analyze_playlist_languages(playlist_id):
    """
    Analyze playlist languages.

    This route analyzes the languages of tracks in a Spotify playlist and returns
    the analysis results. It requires the user to be signed in and have a connected
    Spotify account. It retrieves lyrics for each track in the playlist, analyzes
    them to determine the languages used, and returns the analysis results including
    information about each track, the number of tracks analyzed, and average percentages
    of each language used in the playlist.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.

    Returns:
        dict: A dictionary containing the analysis results, including information
              about each track, the number of tracks analyzed, and average percentages
              of each language used in the playlist.
    """

    # Check if user is signed in
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize SpotifyOAuth manager and Spotify API client
    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)

    # Initialize variables
    lyrics_and_languages = []
    num_tracks_analyzed = 0
    language_totals = {}

    # Function to process tracks
    def process_tracks(tracks):
        nonlocal num_tracks_analyzed, lyrics_and_languages, language_totals
        for item in tracks['items']:
            track_name = item['track']['name']
            artist_name = item['track']['artists'][0]['name']
            lyrics = fetch_lyrics(artist_name, track_name)  # Fetch lyrics for the track
            if lyrics:
                language_results = aggregate_results_from_text(lyrics)  # Analyze lyrics to determine languages used
                sorted_languages = sorted(language_results.items(), key=lambda x: x[1], reverse=True)
                lyrics_and_languages.append({
                    'track_name': track_name,
                    'artist_name': artist_name,
                    'languages': sorted_languages
                })
                num_tracks_analyzed += 1
                for lang, percentage in language_results.items():
                    if lang in language_totals:
                        language_totals[lang] += percentage
                    else:
                        language_totals[lang] = percentage

    # Fetch and process tracks
    try:
        if playlist_id == 'saved_tracks':
            results = spotify.current_user_saved_tracks(limit=50)
        else:
            results = spotify.playlist_tracks(playlist_id, limit=100)

        while results:
            process_tracks(results)
            if results['next']:
                results = spotify.next(results)
            else:
                results = None
    except spotipy.exceptions.SpotifyException as e:
        return jsonify({'error': f'Spotify API error: {e}'}), 400

    # Calculate average language percentages
    average_language_percentages = {}
    if num_tracks_analyzed > 0:
        average_language_percentages = {lang: (total / num_tracks_analyzed) for lang, total in language_totals.items()}
        sorted_average_languages = sorted(average_language_percentages.items(), key=lambda x: x[1], reverse=True)

    # Prepare the response
    return jsonify({
        'analysis_results': lyrics_and_languages,
        'num_tracks_analyzed': num_tracks_analyzed,
        'average_languages': {lang: percentage for lang, percentage in sorted_average_languages}
    })


@main.route('/create_playlist_from_liked_songs')
def create_playlist_from_liked_songs():
    """
    Create a playlist from liked songs.

    This route creates a new playlist from the user's liked songs in Spotify.
    It requires the user to be signed in and have a connected Spotify account.
    It fetches all the user's saved tracks, creates a new playlist named "Complete
    Liked Songs Playlist", and adds all the saved tracks to the new playlist.

    Returns:
        dict: A dictionary containing a message indicating the success of playlist creation
              and the ID of the newly created playlist.
    """

    # Check if user is signed in
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize Spotify API client
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    # Get user's Spotify ID
    user_id = spotify.current_user()['id']
    
    # Fetch all user's saved tracks with pagination
    results = spotify.current_user_saved_tracks(limit=50)
    track_uris = [item['track']['uri'] for item in results['items'] if item['track']]
    while results['next']:
        results = spotify.next(results)
        track_uris.extend([item['track']['uri'] for item in results['items'] if item['track']])
    
    # Create a new playlist
    playlist_name = "Complete Liked Songs Playlist"
    new_playlist = spotify.user_playlist_create(user_id, playlist_name, public=True)

    # Due to limitations, add tracks in batches of 100
    for i in range(0, len(track_uris), 100):
        spotify.playlist_add_items(new_playlist['id'], track_uris[i:i+100])

    return jsonify({'message': 'Playlist created successfully', 'playlist_id': new_playlist['id']})


@main.route('/playlist_analysis')
def playlist_analysis():
    """
    Perform analysis on user's Spotify playlists.

    This route checks if the user is logged in and has connected their Spotify account.
    If the user is logged in and has a connected Spotify account, it retrieves the user's
    playlists from Spotify and renders a template for playlist analysis, passing the
    playlists data to the template. If the user is not logged in, it flashes a message
    prompting the user to log in. If the user is logged in but has not connected their
    Spotify account, it flashes a message prompting the user to connect their Spotify
    account.

    Returns:
        str: Renders the playlist analysis template with the playlists data if the user
             is logged in and has a connected Spotify account.
        str: Redirects the user to the sign-in page if the user is not logged in.
        str: Redirects the user to the Spotify connection page if the user is logged in
             but has not connected their Spotify account.
    """

    # Check if user is logged in
    if 'user_id' not in session:
        # Flash message indicating that the user needs to log in
        flash("You need to log in to access this feature.")

        # Redirect user to the sign-in page
        return redirect(url_for('main.signin'))
    
    user_id = session['user_id']
    
    # Check if user has connected their Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if user_oauth and user_oauth.spotify_access_token:
        # Initialize Spotify API client
        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(user_id)))
        
        # Fetch user's playlists from Spotify
        playlists = spotify.current_user_playlists(limit=50)
        
        # Extract playlist name and ID from fetched data
        playlists = [{'name': playlist['name'], 'id': playlist['id']} for playlist in playlists['items']]
    else:
        # Flash message indicating that the user needs to connect their Spotify account
        flash("Please connect your Spotify account.")

        # Redirect user to the Spotify connection page
        return redirect(url_for('main.connect_spotify'))
    
    # Render the playlist analysis template with playlists data
    return render_template('playlist_analysis.html', playlists=playlists, user=g.user)


def analyze_sentiments(lyrics):
    blob = TextBlob(lyrics)
    return blob.sentiment.polarity  # Returns a polarity score between -1 and 1


@main.route('/analyze_playlist_sentiments/<playlist_id>')
def analyze_playlist_sentiments(playlist_id):
    """
    Analyze sentiment of tracks in a Spotify playlist.

    This route analyzes the sentiment of tracks in a Spotify playlist by fetching
    the lyrics of each track and calculating the sentiment score using TextBlob.
    It requires the user to be signed in and have a connected Spotify account.
    It returns the average sentiment score of the tracks in the playlist along
    with the sentiment score of each individual track.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.

    Returns:
        dict: A dictionary containing the average sentiment score of the playlist
              and sentiment scores of each individual track.
    """

    # Check if user is signed in
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize Spotify API client
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    # Fetch the tracks in the playlist and analyze their sentiments
    try:
        results = spotify.playlist_tracks(playlist_id, limit=100)
        track_sentiments = []
        for item in results['items']:
            track = item['track']
            track_name = track['name']
            lyrics = fetch_lyrics(track['artists'][0]['name'], track_name)  # Fetch lyrics for the track
            if lyrics:
                blob = TextBlob(lyrics)
                sentiment_score = blob.sentiment.polarity  # Calculate sentiment score using TextBlob
                track_sentiments.append({
                    'track_name': track_name,
                    'sentiment': sentiment_score
                })

        # Calculate average sentiment score of the playlist
        if track_sentiments:
            average_sentiment = sum([d['sentiment'] for d in track_sentiments]) / len(track_sentiments)
        else:
            average_sentiment = 0

        # Return the average sentiment score and sentiment scores of each individual track
        return jsonify({
            'average_sentiment': average_sentiment,
            'track_sentiments': track_sentiments
        })

    except Exception as e:
        # Return error message if an exception occurs during analysis
        return jsonify({'error': str(e)}), 500

    
@main.route('/analyze_playlist_genres_and_sentiments/<playlist_id>')
def analyze_playlist_genres_and_sentiments(playlist_id):
    """
    Analyze genres and sentiments of tracks in a Spotify playlist.

    This route analyzes the genres and sentiments of tracks in a Spotify playlist
    by fetching the details of each track, including genres of the artists and
    sentiment scores of the lyrics. It requires the user to be signed in and have
    a connected Spotify account. It returns the average sentiment score of the
    tracks in the playlist along with the detailed information of each individual track.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.

    Returns:
        dict: A dictionary containing the average sentiment score of the playlist,
              and detailed information of each individual track including track name,
              sentiment score, and genres of the artists.
    """

    # Check if user is signed in
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize Spotify API client
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    try:
        # Fetch the tracks in the playlist
        results = spotify.playlist_tracks(playlist_id, limit=100)
        track_details = []

        # Iterate over each track in the playlist
        for item in results['items']:
            track = item['track']
            track_name = track['name']
            artists = track['artists']
            genres = set()

            # Fetch genres of each artist in the track
            for artist in artists:
                artist_data = spotify.artist(artist['id'])
                genres.update(artist_data.get('genres', []))

            # Fetch lyrics and calculate sentiment score if available
            lyrics = fetch_lyrics(track['artists'][0]['name'], track_name)
            sentiment_score = None
            if lyrics:
                blob = TextBlob(lyrics)
                sentiment_score = blob.sentiment.polarity
            
            # Append track details to the list
            track_details.append({
                'track_name': track_name,
                'sentiment': sentiment_score,
                'genres': list(genres)  # Convert the set to a list for JSON serialization
            })
        
        # Calculate the average sentiment score of the playlist
        sentiments = [detail['sentiment'] for detail in track_details if detail['sentiment'] is not None]
        average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Return the average sentiment score and track details
        return jsonify({
            'average_sentiment': average_sentiment,
            'tracks': track_details
        })

    except Exception as e:
        # Return error message if an exception occurs during analysis
        return jsonify({'error': str(e)}), 500


@main.route('/analyze_playlist_genres/<playlist_id>')
def analyze_playlist_genres(playlist_id):
    """
    Analyze genres of artists in a Spotify playlist.

    This route analyzes the genres of artists in a Spotify playlist by fetching
    the details of each track and counting the occurrences of each genre. It
    requires the user to be signed in and have a connected Spotify account.
    It returns the counts of each genre present in the playlist.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.

    Returns:
        dict: A dictionary containing the counts of each genre present in the playlist.
    """

    # Check if user is signed in
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize Spotify API client
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    try:
        # Fetch the tracks in the playlist
        results = spotify.playlist_tracks(playlist_id, limit=100)
        genre_counts = {}

        # Iterate over each track in the playlist
        for item in results['items']:
            track = item['track']
            artists = track['artists']

            # Iterate over each artist in the track
            for artist in artists:
                artist_data = spotify.artist(artist['id'])

                # Fetch genres of the artist and update genre counts
                for genre in artist_data.get('genres', []):
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Return the counts of each genre present in the playlist
        return jsonify({'genre_counts': genre_counts})

    except Exception as e:
        # Return error message if an exception occurs during analysis
        return jsonify({'error': str(e)}), 500


@main.route('/create_language_playlists/<playlist_id>/<level>', methods=['GET'])
def create_language_playlists(playlist_id, level):
    """
    Create playlists for songs based on language and percentage threshold.

    This route creates playlists for songs based on their language and a specified
    percentage threshold. It requires the user to be signed in and have a connected
    Spotify account. It analyzes the tracks in the specified playlist, aggregates
    the languages of the lyrics, and creates playlists for each language based on
    the specified threshold level.

    Args:
        playlist_id (str): The ID of the Spotify playlist to analyze.
        level (str): The threshold level for including tracks in playlists. Possible
                     values are 'high', 'medium', 'low'.

    Returns:
        dict: A dictionary containing a message indicating the success of playlist
              creation and the IDs of the playlists created for each language.
    """

    # Check if user is signed in
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    # Check if user has a connected Spotify account
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    # Initialize Spotify API client
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    # Initialize variables
    languages_data = {}
    created_playlists = {}

    try:
        # Fetch the tracks in the playlist and aggregate languages and percentages
        results = spotify.playlist_tracks(playlist_id)
        while results:
            for item in results['items']:
                track = item['track']
                lyrics = fetch_lyrics(track['artists'][0]['name'], track['name'])
                if lyrics:
                    language_results = aggregate_results_from_text(lyrics)
                    for language, percentage in language_results.items():
                        if language not in languages_data:
                            languages_data[language] = []
                        languages_data[language].append((track['uri'], percentage))

            results = spotify.next(results) if results['next'] else None
    except Exception as e:
        return jsonify({'error': 'Error fetching or processing tracks: ' + str(e)}), 500

    # Define threshold levels
    threshold = {
        'high': 0.75,
        'medium': 0.25,
        'low': 0.10
    }.get(level, 0.10)

    # Get the Spotify user ID
    spotify_user_id = spotify.current_user()['id']

    # Create playlists for each language based on threshold
    for language, track_info in languages_data.items():
        playlist_uris = [uri for uri, percentage in track_info if percentage >= threshold]
        if playlist_uris:
            playlist_name = f"{language} Songs - {level.capitalize()}"
            try:
                playlist = spotify.user_playlist_create(spotify_user_id, playlist_name, public=True)
                if playlist:
                    batch_add_tracks(spotify, playlist['id'], playlist_uris)
                    created_playlists[language] = playlist['id']
                else:
                    print(f"Failed to create playlist: {playlist_name}")
            except Exception as e:
                print(f"Error creating or populating playlist {playlist_name}: {e}")

    # Return success message and created playlist IDs
    return jsonify({
        'message': 'Playlists created successfully',
        'playlists': created_playlists
    })


@main.route('/delete_test_playlists', methods=['GET'])
def delete_test_playlists():
    if 'user_id' not in session:
        flash('You must be logged in to delete playlists.')
        return redirect(url_for('main.signin'))

    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        flash('Spotify connection is required.')
        return redirect(url_for('main.connect_spotify'))

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
    
    # Fetch all playlists from the user's account
    try:
        playlists = spotify.current_user_playlists()
        delete_count = 0
        for playlist in playlists['items']:
            # Look for playlists with names containing 'High', 'Medium', or 'Low'
            if any(level in playlist['name'] for level in ['High', 'Medium', 'Low']):
                spotify.current_user_unfollow_playlist(playlist['id'])
                delete_count += 1

        flash(f'Successfully deleted {delete_count} test playlists.')
    except spotipy.exceptions.SpotifyException as e:
        flash(f'An error occurred while trying to delete playlists: {e}')
        return redirect(url_for('main.dashboard'))

    return redirect(url_for('main.dashboard'))