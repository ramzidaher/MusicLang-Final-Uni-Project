from flask import Blueprint, g, jsonify, render_template, redirect, url_for, session, request, flash
from .models import User, UserOAuth
from .forms import LoginForm, RegistrationForm  # Import your forms
from .utils import allowed_file, get_language_name, predict_languages_for_line,aggregate_results_from_text,get_playlist_count,get_genius_client,fetch_lyrics,get_playlist_tracks_with_lyrics    # Import utility functions
from . import db
from werkzeug.utils import secure_filename
from spotipy.oauth2 import SpotifyOAuth  # Import SpotifyOAuth
import os
import spotipy
# routes.py
from .helpers import session_cache_path


from flask import current_app

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}




# Routes


#Main Route
@main.route('/')
def index():
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
    if 'user_id' not in session:
        flash('You must be logged in to connect your Spotify account.')
        return redirect(url_for('main.signin'))

    # In your existing /connect_spotify route
    scope = "playlist-modify-public playlist-modify-private user-read-private user-read-email"
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
    auth_url = oauth_manager.get_authorize_url()
    return redirect(auth_url)




# @main.route('/connect_spotify')
# def connect_spotify():
#     """
#     Connect the user's Spotify account.

#     This route checks if the user is logged in by verifying the presence of 'user_id' in the session.
#     If the user is logged in, it generates the Spotify OAuth authorization URL and redirects the user
#     to that URL to authorize the application's access to their Spotify account. If the user is not logged
#     in, it flashes a message indicating that the user must be logged in to connect their Spotify account
#     and redirects them to the sign-in page.

#     Args:
#         None

#     Returns:
#         str: Redirects the user to the Spotify OAuth authorization URL if logged in.
#         str: Redirects the user to the sign-in page if not logged in.

#     """
#     if 'user_id' not in session:
#         flash('You must be logged in to connect your Spotify account.')
#         return redirect(url_for('main.signin'))

#     # Update Spotify OAuth scope to include playlist modification permissions
#     scope = "playlist-modify-public playlist-modify-private user-read-private user-read-email"
#     oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
#     auth_url = oauth_manager.get_authorize_url()
#     return redirect(auth_url)

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
    elif playlist_id:
        # Display tracks for a specific playlist for potential analysis
        return get_playlist_tracks_with_lyrics(user_id, playlist_id)
    else:
        # Initial page load, show user playlists
        return fetch_user_playlists(user_id)


def fetch_user_playlists(user_id):
    """
    Fetch playlists for the specified user from Spotify.

    This function retrieves the user's playlists from Spotify using the user's
    OAuth token. If the user has connected their Spotify account and there's
    an access token available, it fetches the playlists and renders a template
    displaying them.

    If the user has not connected their Spotify account or there's no access token
    available, it flashes a message indicating that the user needs to connect to
    Spotify and redirects them to the dashboard.

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
        
        # Add the user's saved tracks as a pseudo-playlist
        saved_tracks_pseudo_playlist = {'name': 'Liked Songs', 'id': 'saved_tracks'}
        
        # Combine the pseudo-playlist with the actual playlists
        playlists = [saved_tracks_pseudo_playlist] + \
                    [{'name': playlist['name'], 'id': playlist['id']} for playlist in results['items']]
                    
        return render_template('feature_analyze.html', playlists=playlists, user=g.user)
    else:
        flash('Please connect to Spotify.', 'info')
        return redirect(url_for('main.dashboard'))





# @main.route('/api/playlist_tracks/<playlist_id>')
# def api_playlist_tracks(playlist_id):
    """
    Retrieve tracks from a Spotify playlist or user's saved tracks.

    This endpoint returns the tracks contained in a Spotify playlist specified
    by `playlist_id` or the user's saved tracks if `playlist_id` is 'saved_tracks'.

    Args:
        playlist_id (str): The ID of the playlist or 'saved_tracks' for user's saved tracks.

    Returns:
        dict: A dictionary containing the retrieved tracks. The 'tracks' key contains a list of dictionaries,
              each representing a track with 'name' and 'artist' keys.


    """
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
            results = spotify.next(results) if results['next'] else None
    else:
        # Fetch tracks from a specific playlist
        results = spotify.playlist_tracks(playlist_id, limit=100)
        while results:
            tracks.extend([{'name': item['track']['name'],
                            'artist': ', '.join(artist['name'] for artist in item['track']['artists'])}
                           for item in results['items'] if item['track']])
            results = spotify.next(results) if results['next'] else None

    return {'tracks': tracks}

from spotipy import SpotifyOAuth
import spotipy
from flask import session, jsonify

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






# @main.route('/analyze_playlist_languages/<playlist_id>')
# def analyze_playlist_languages(playlist_id):
#     if 'user_id' not in session:
#         return jsonify({'error': 'User not signed in'}), 401

#     user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
#     if not user_oauth or not user_oauth.spotify_access_token:
#         return jsonify({'error': 'Spotify connection is required.'}), 403

#     spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
#     try:
#         tracks_data = spotify.playlist_tracks(playlist_id)
#     except spotipy.exceptions.SpotifyException as e:
#         return jsonify({'error': f'Spotify API error: {e}'}), 400

#     # Aggregate language results from the lyrics
#     language_totals = {}
#     for item in tracks_data['items']:
#         track = item['track']
#         lyrics = fetch_lyrics(track['artists'][0]['name'], track['name'])
#         if lyrics:
#             language_results = aggregate_results_from_text(lyrics)
#             for lang, percentage in language_results.items():
#                 language_totals[lang] = language_totals.get(lang, 0) + percentage

#     # Normalize and sort language results
#     total_percentage = sum(language_totals.values())
#     sorted_languages = sorted(
#         ((lang, percent / total_percentage * 100) for lang, percent in language_totals.items()),
#         key=lambda x: x[1],
#         reverse=True
#     )

#     # Prepare data for different playlist levels
#     return jsonify({
#         'playlist_id': playlist_id,
#         'languages': sorted_languages,
#         'tracks_analyzed': len(tracks_data['items'])
#     })



# @main.route('/create_language_playlists/<playlist_id>', methods=['GET'])
# def create_language_playlists(playlist_id):
#     user_id = session.get('user_id')
#     if not user_id:
#         return jsonify({'error': 'User not signed in'}), 401

#     user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
#     if not user_oauth or not user_oauth.spotify_access_token:
#         return jsonify({'error': 'Spotify connection is required.'}), 403

#     oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
#     spotify = spotipy.Spotify(auth_manager=oauth_manager)

#     # Token Refresh and Error Handling
#     token_info = oauth_manager.get_cached_token()
#     if oauth_manager.is_token_expired(token_info):
#         token_info = oauth_manager.refresh_access_token(token_info['refresh_token'])
#         spotify.auth = token_info['access_token']

#     try:
#         # Retrieve Spotify User ID
#         spotify_user_id = spotify.current_user()['id']

#         # Fetching the playlist's tracks
#         tracks_data = spotify.playlist_tracks(playlist_id)
        
#         # Analyze languages and organize tracks
#         tracks_by_language = {}
#         language_threshold = 0.40  # 40% threshold for language detection
#         for item in tracks_data['items']:
#             track = item['track']
#             track_name = track['name']
#             artist_name = track['artists'][0]['name']
#             lyrics = fetch_lyrics(artist_name, track_name)

#             if lyrics:
#                 language_results = aggregate_results_from_text(lyrics)
#                 for language, percentage in language_results.items():
#                     if percentage >= language_threshold:
#                         if language not in tracks_by_language:
#                             tracks_by_language[language] = []
#                         tracks_by_language[language].append(track['uri'])

#         # Create new playlists for each language and add tracks
#         created_playlists = {}
#         for language, track_uris in tracks_by_language.items():
#             playlist_name = f"{language.capitalize()} Songs"
#             new_playlist = spotify.user_playlist_create(spotify_user_id, playlist_name)
#             spotify.playlist_add_items(new_playlist['id'], track_uris)
#             created_playlists[language] = new_playlist['id']

#         return jsonify({'message': 'Playlists created successfully', 'playlists': created_playlists})

#     except spotipy.SpotifyException as e:
#         if e.http_status == 401:
#             # Redirect to re-authentication
#             return redirect(url_for('reauthenticate_spotify'))
#         elif e.http_status == 403:
#             # Handle insufficient scope
#             flash('Insufficient permissions to access Spotify data')
#             return redirect(url_for('main.dashboard'))
#         else:
#             # General error handling
#             flash('An error occurred while accessing Spotify')
#             return redirect(url_for('main.dashboard'))






# Add this route to your Flask application
@main.route('/reauthenticate_spotify')
def reauthenticate_spotify():
    if 'user_id' not in session:
        flash('You must be logged in to reconnect your Spotify account.')
        return redirect(url_for('main.signin'))

    scope = "playlist-modify-public playlist-modify-private user-read-private user-read-email"
    oauth_manager = SpotifyOAuth(scope=scope, cache_path=session_cache_path(session['user_id']))
    auth_url = oauth_manager.get_authorize_url()
    return redirect(auth_url)


@main.route('/api/all_saved_tracks')
def all_saved_tracks():
    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
    tracks = []
    results = spotify.current_user_saved_tracks()
    while results:
        try:
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
            print("Failed to fetch tracks:", str(e))
            break

    return jsonify({'tracks': tracks})



from flask import request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .models import UserOAuth
from .utils import session_cache_path, fetch_lyrics, aggregate_results_from_text

from flask import jsonify, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth

@main.route('/create_language_playlists/<playlist_id>/<level>', methods=['GET'])
def create_language_playlists(playlist_id, level):
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))

    # Initialize data structure for language-specific tracks
    languages_data = {}

    # Fetch the playlist's tracks and handle pagination
    try:
        results = spotify.playlist_tracks(playlist_id)
        while results:
            for item in results['items']:
                track = item['track']
                lyrics = fetch_lyrics(track['artists'][0]['name'], track['name'])
                if lyrics:
                    language_results = aggregate_results_from_text(lyrics)
                    for language, percentage in language_results.items():
                        if percentage >= 0.25:  # Threshold for medium complexity
                            if language not in languages_data:
                                languages_data[language] = []
                            languages_data[language].append(track['uri'])

            if results['next']:  # Check if there is another page of tracks
                results = spotify.next(results)
            else:
                break
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Create playlists based on the analysis level
    created_playlists = {}
    spotify_user_id = spotify.current_user()['id']
    if level == 'medium':
        for lang, uris in languages_data.items():
            if uris:
                playlist_name = f"{lang} Songs"
                playlist = spotify.user_playlist_create(spotify_user_id, playlist_name, public=True)
                spotify.playlist_add_items(playlist['id'], uris)
                created_playlists[lang] = playlist['id']
    elif level == 'low' or level == 'high':
        # Add handling for 'low' and 'high' complexity levels as needed
        pass

    return jsonify({
        'message': 'Playlists created successfully',
        'playlists': created_playlists
    })





@main.route('/delete_specific_playlists', methods=['GET'])
def delete_specific_playlists():
    # Confirmation step or logic to ensure this action is intentional
    # ...

    if 'user_id' not in session:
        flash('You must be logged in to delete playlists.')
        return redirect(url_for('main.signin'))

    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        flash('Spotify connection is required.')
        return redirect(url_for('main.connect_spotify'))

    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(session['user_id']))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)

    # Check if the token is expired and refresh it
    token_info = oauth_manager.get_cached_token()
    if oauth_manager.is_token_expired(token_info):
        token_info = oauth_manager.refresh_access_token(token_info['refresh_token'])
        spotify.auth = token_info['access_token']

    # Fetch the current user's Spotify ID
    current_spotify_user = spotify.current_user()
    spotify_user_id = current_spotify_user['id']

    # The names of the playlists you want to delete (based on the image provided)
    playlist_names_to_delete = [
        "English Songs","Egyptian arabic Songs", "Other Languages Songs", "Arabic Songs", "Egyptian Arabic Songs", "French Songs",
        "Portuguese Songs", "Italian Songs", "Spanish Songs", "Dutch Songs",
        "Korean Songs", "German Songs", "Turkish Songs"
    ]

    try:
        playlists = spotify.current_user_playlists(limit=50)
        for playlist in playlists['items']:
            # Use the fetched Spotify user ID for comparison
            if playlist['name'] in playlist_names_to_delete and playlist['owner']['id'] == spotify_user_id:
                spotify.current_user_unfollow_playlist(playlist['id'])
        flash('Specified playlists deleted successfully.')
    except spotipy.exceptions.SpotifyException as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('main.dashboard'))

    return redirect(url_for('main.dashboard'))




@main.route('/analyze_playlist_languages/<playlist_id>')
def analyze_playlist_languages(playlist_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not signed in'}), 401

    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)

    lyrics_and_languages = []
    num_tracks_analyzed = 0
    language_totals = {}

    # Function to process tracks
    def process_tracks(tracks):
        nonlocal num_tracks_analyzed, lyrics_and_languages, language_totals
        for item in tracks['items']:
            track_name = item['track']['name']
            artist_name = item['track']['artists'][0]['name']
            lyrics = fetch_lyrics(artist_name, track_name)
            if lyrics:
                language_results = aggregate_results_from_text(lyrics)
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
    if 'user_id' not in session:
        return jsonify({'error': 'User not signed in'}), 401

    user_oauth = UserOAuth.query.filter_by(user_id=session['user_id']).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        return jsonify({'error': 'Spotify connection is required.'}), 403

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(cache_path=session_cache_path(session['user_id'])))
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
