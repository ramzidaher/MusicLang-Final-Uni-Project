# Import necessary libraries
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius



# Genius access token
genius_access_token = 'oapCISWxA039oLY7GSl9D6BgUM2l-CcYlQQJPgrYrgieF72fHI7JzwO6jRXgm5_D-'

# Initialize Spotify clien

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

