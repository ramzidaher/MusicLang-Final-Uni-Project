import fasttext
from flask import flash, redirect, render_template, session, url_for
import pycountry
import spotipy
from spotipy.oauth2 import SpotifyOAuth  # Import SpotifyOAuth
from .models import User, UserOAuth
# utils.py
from .helpers import session_cache_path
from lyricsgenius import Genius
from flask import current_app
from lyricsgenius import Genius



model_path = 'lid.176.bin'

model = fasttext.load_model(model_path)



ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS






def predict_languages_for_line(line, threshold=0.01):
    """Predicts languages for a single line, considering the distribution.

    Args:
        line (str): The input text line.
        threshold (float): The minimum percentage to consider for inclusion.

    Returns:
        dict: A dictionary with language names as keys and their percentages as values.
    """
    predictions = model.predict(line, k=-1)
    languages, probabilities = predictions
    total_prob = sum(probabilities)

    results = {}
    for lang, prob in zip(languages, probabilities):
        percentage = (prob / total_prob) * 100
        if percentage >= threshold:
            lang_code = lang.replace('__label__', '')
            lang_name = get_language_name(lang_code)
            results[lang_name] = percentage
    return results

def aggregate_results_from_text(text, initial_threshold=0.01, final_threshold=5.0):
    """Aggregates language detection results across the entire text, applying an initial threshold for detection
    and a final threshold for inclusion in the final results. Re-normalizes percentages of languages meeting the
    final threshold to ensure they sum to 100%.

    Args:
        text (str): The input text.
        initial_threshold (float): Initial threshold for including a language in the intermediate results.
        final_threshold (float): Final threshold for including a language in the final results.

    Returns:
        dict: Aggregated and re-normalized language percentages.
    """
    aggregated_results = {}
    lines = text.split('\n')
    for line in lines:
        if line.strip():  # Ensure the line is not empty
            line_results = predict_languages_for_line(line, initial_threshold)
            for lang, percentage in line_results.items():
                if lang in aggregated_results:
                    aggregated_results[lang] += percentage
                else:
                    aggregated_results[lang] = percentage

    # Normalize to ensure percentages sum to 100%
    total_percentage = sum(aggregated_results.values())
    normalized_results = {lang: (percentage / total_percentage) * 100 for lang, percentage in aggregated_results.items()}

    # Apply the final threshold to filter the results
    final_results = {lang: percentage for lang, percentage in normalized_results.items() if percentage >= final_threshold}

    # Re-normalize final results to ensure they sum up to 100%
    final_total_percentage = sum(final_results.values())
    re_normalized_final_results = {lang: (percentage / final_total_percentage) * 100 for lang, percentage in final_results.items()}

    return re_normalized_final_results


def get_playlist_count(spotify):
    total_playlists_created_by_user = 0
    playlists = spotify.current_user_playlists()
    
    while playlists:
        for playlist in playlists['items']:
            # Check if the current user is the owner of the playlist
            if playlist['owner']['id'] == spotify.me()['id']:
                total_playlists_created_by_user += 1
        
        # Spotify paginates playlists, so check if there are more to fetch
        if playlists['next']:
            playlists = spotify.next(playlists)
        else:
            playlists = None

    return total_playlists_created_by_user


def get_playlist_tracks_with_lyrics(user_id, playlist_id):
    """
    Fetch tracks of a specified playlist from Spotify.

    This function fetches tracks of a specified playlist from Spotify using the
    user's OAuth token. If the user has not connected their Spotify account or there's
    no access token available, it flashes a message indicating that the user needs to
    connect to Spotify and redirects them to the dashboard.

    If there are errors encountered during fetching, it flashes an error message
    and redirects the user to the dashboard.

    Args:
        user_id (int): The ID of the user whose playlist tracks are to be fetched.
        playlist_id (str): The ID of the playlist whose tracks are to be fetched.

    Returns:d
        str: Renders the page with the playlist tracks for potential analysis.
        str: Redirects the user to the dashboard if Spotify connection fails or errors occur during fetching.

    """
    user_oauth = UserOAuth.query.filter_by(user_id=user_id).first()
    if not user_oauth or not user_oauth.spotify_access_token:
        flash('Spotify connection is required.', 'info')
        return redirect(url_for('main.dashboard'))

    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)

    try:
        if playlist_id == 'saved_tracks':
            # Fetch liked songs
            results = spotify.current_user_saved_tracks()
        else:
            # Fetch tracks from a regular playlist
            results = spotify.playlist_tracks(playlist_id)

        tracks = [{
            'name': item['track']['name'],
            'artist': item['track']['artists'][0]['name'],
            'lyrics_url': "Dummy Lyrics URL"  # Implement actual lyrics fetching here
        } for item in results['items'] if item['track']]
        
        return render_template('feature_analyze.html', tracks=tracks, playlist_id=playlist_id)

    except spotipy.exceptions.SpotifyException as e:
        flash(f'Error fetching tracks: {e}', 'error')
        return redirect(url_for('main.dashboard'))

    oauth_manager = SpotifyOAuth(cache_path=session_cache_path(user_id))
    spotify = spotipy.Spotify(auth_manager=oauth_manager)
    tracks_data = spotify.playlist_tracks(playlist_id)
    tracks = [{'name': item['track']['name'], 'artist': item['track']['artists'][0]['name'], 'lyrics_url': "Dummy Lyrics URL"} for item in tracks_data['items']]  # Implement actual lyrics fetching here
    return render_template('feature_analyze.html', tracks=tracks, playlist_id=playlist_id)




def get_user_playlists():
    """
    Retrieve playlists of the currently logged-in Spotify user.

    This function retrieves the playlists of the currently logged-in Spotify user.
    It requires the user to be logged in, and the session must contain the 'user_id'.

    Returns:
        dict or None: A dictionary containing the user's playlists if the user is logged in,
                      otherwise returns None.
    """
    if 'user_id' in session:
        oauth_manager = SpotifyOAuth(cache_path=session_cache_path(session['user_id']))
        spotify = spotipy.Spotify(auth_manager=oauth_manager)
        playlists = spotify.current_user_playlists()
        return playlists
    else:
        # Handle the case where the user is not logged in or session is expired
        return None


def get_genius_client():
    """
    Retrieve the Genius client.

    This function checks if the Genius client has already been initialized.
    If not, it initializes the Genius client and stores it in the app config.

    Returns:
        Genius: The Genius client instance.

    """
    # Check if the Genius client has already been initialized
    if 'genius_client' not in current_app.config:
        # Initialize the Genius client and store it in the app config
        current_app.config['genius_client'] = Genius(current_app.config['GENIUS_ACCESS_TOKEN'])
    return current_app.config['genius_client']


def fetch_lyrics(artist, title):
    """
    Fetch lyrics for a given artist and title using the Genius API.

    This function fetches lyrics for a given artist and title using the Genius API.
    It requires the artist name and the title of the song.

    Args:
        artist (str): The name of the artist.
        title (str): The title of the song.

    Returns:
        str or None: The lyrics of the song if found, otherwise returns None.
    """
    genius = get_genius_client()  # Get the Genius client
    song = genius.search_song(title, artist)
    if song:
        return song.lyrics
    return None


def get_language_name(iso_code):
    """
    Fetches the full language name given its ISO code.

    This function fetches the full language name given its ISO code.
    It first attempts to find the language using the ISO 639-1 code,
    and if not found, it tries using the ISO 639-2 code.

    Args:
        iso_code (str): The ISO code of the language.

    Returns:
        str: The full name of the language if found, otherwise returns the ISO code.

    """
    language = pycountry.languages.get(alpha_2=iso_code)
    if language is not None:
        return language.name
    language = pycountry.languages.get(alpha_3=iso_code)
    if language is not None:
        return language.name
    return iso_code
