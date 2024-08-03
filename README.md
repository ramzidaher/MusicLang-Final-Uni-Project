# MusicLang: Multilingual Lyrics Analysis

## Overview

MusicLang is a web application developed as a final year university project. It is designed to analyze and categorize song lyrics in various languages, providing insights into cultural and linguistic diversity. Built with Flask, this tool leverages FastText to offer detailed analysis and insights into the lyrics of your favorite songs.

## Features

- **Multilingual Lyrics Analysis**: Utilizes the `lid.176.bin` language identification model from FastText to accurately determine the language of the lyrics and analyze them accordingly.
- **FastText Model Integration**: Analyzes lyrics using FastText for nuanced understanding and interpretation.
- **Playlist Management**: Create, manage, and categorize playlists based on the languages of the songs.
- **Spotify Integration**: Fetch insights directly from Spotify, including track details and user preferences.
- **User Authentication**: Secure login and registration system to save your analyses and playlists.

## Installation

### Prerequisites

- Python 3.8 or higher
- Pipenv for dependency management
- Install lib.175.bin https://fasttext.cc/docs/en/language-identification.html
- Python 3.7+
- Flask
- Spotify API credentials
- Required Python packages (see `requirements.txt`)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ramzidaher/MusicLang-Final-Uni-Project.git
   cd MusicLang-Final-Uni-Project
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory and add your Spotify API credentials:
   ```env
   SPOTIPY_CLIENT_ID='your-spotify-client-id'
   SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
   SPOTIPY_REDIRECT_URI='your-spotify-redirect-uri'
   GENIUS_ACCESS_TOKEN='your-genius-access-token'
   ```

5. **Run the application**:
   ```bash
   flask run
   ```

## Usage

1. Navigate to `http://127.0.0.1:5000` in your web browser.
2. Register or log in to access the full features of the application.
3. Upload lyrics or connect your Spotify account to start analyzing songs.
4. Create and manage playlists, and view detailed analysis of each song's lyrics.
5. Playlists are categorized based on the language detected in the lyrics, providing insights into your musical preferences and diversity.

## Analysis Process

1. **Lyrics Input**: Users can input song lyrics directly or fetch lyrics from their Spotify playlists.
2. **Language Detection**: The `lid.176.bin` model from FastText is used to detect the language of the lyrics.
3. **Lyrics Analysis**: The detected language helps tailor the analysis process, providing insights based on linguistic characteristics.
4. **Categorization**: Songs are categorized into playlists based on the detected language, allowing users to explore their music library's linguistic diversity.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

For any questions or feedback, please contact me.

By ensuring clear, consistent formatting and including all necessary details, you can minimize the likelihood of conflicts and make the README file more user-friendly. If there are specific conflicts or errors you encountered, please provide more details so I can offer targeted assistance.
