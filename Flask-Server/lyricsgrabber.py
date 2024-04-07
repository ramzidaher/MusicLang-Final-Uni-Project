# Import necessary libraries
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius

# Spotify credentials (replace these with your actual credentials)
spotify_client_id = '9ee0338fe3e74fc998cbff50462a3241'
spotify_client_secret = '37f7c65ea65149a3aa8936663a606152'

# Genius access token
genius_access_token = 'VSGWz90P3LMTwqWyAvPhaM_pwe7wgZBOkpd2yB67JCY9PNRGqesI17HJc0GxsBg-'

# Initialize Spotify client
spotify_auth_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
sp = spotipy.Spotify(auth_manager=spotify_auth_manager)

# Initialize Genius client
genius = Genius(genius_access_token)

def get_song_lyrics(song_name, artist_name=None):
    # Adjusted search to include artist name for more accuracy
    query = song_name if artist_name is None else f"{song_name} {artist_name}"
    results = sp.search(q=query, limit=1)
    if not results['tracks']['items']:
        print("Song not found on Spotify.")
        return

    song_info = results['tracks']['items'][0]
    artist_name_spotify = song_info['artists'][0]['name']

    # Try searching with the specific artist name if provided
    search_artist_name = artist_name if artist_name is not None else artist_name_spotify
    song = genius.search_song(title=song_name, artist=search_artist_name)
    if song:
        return song.lyrics
    else:
        print("Lyrics not found on Genius.")
        return

# Adjust the song name or artist name if you have better or more accurate details
lyrics = get_song_lyrics("Inn Ann", "Daboor")
if lyrics:
    print(lyrics)
else:
    # If the correct lyrics are still not found, consider handling the exception more gracefully
    print("Unable to retrieve correct lyrics. Consider manual retrieval from Genius.")

