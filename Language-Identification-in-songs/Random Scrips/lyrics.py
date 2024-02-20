import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Replace these with your actual credentials
CLIENT_ID = '17d33590c77d4837887189bd1d8a0f17'
CLIENT_SECRET = '65aeb214850d40b099b090b474a2966f'
REDIRECT_URI = "http://localhost:8888/callback"  # This should be set in your Spotify app settings
SCOPE = 'user-library-read playlist-modify-public playlist-modify-private'
MUSIXMATCH_API_KEY = '382520b1aa646f1776957c4e5515d932'  # replace with your API key

# Initialize the Spotify API client with your credentials
auth_manager = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=SCOPE)
sp = spotipy.Spotify(auth_manager=auth_manager)

def get_lyrics(artists, track_name):
    base_url = 'https://api.musixmatch.com/ws/1.1/'
    method = 'matcher.lyrics.get'
    artist_name = " & ".join(artists)
    params = {
        'format': 'json',
        'callback': 'callback',
        'q_track': track_name,
        'q_artist': artist_name,
        'apikey': MUSIXMATCH_API_KEY,
    }

    response = requests.get(base_url + method, params=params)
    data = response.json()

    try:
        lyrics = data['message']['body']['lyrics']['lyrics_body']
        print(f'Lyrics for {track_name} by {artist_name}:\n{lyrics}')
        with open('lyrics.txt', 'w') as file:
            file.write(f'Lyrics for {track_name} by {artist_name}:\n{lyrics}')
    except KeyError:
        print(f'Could not find lyrics for {track_name} by {artist_name}.')

get_lyrics(['', 'Elyanna'], 'Ala Bali')
