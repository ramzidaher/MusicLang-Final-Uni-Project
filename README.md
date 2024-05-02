
# MusicLang

MusicLang is a web application that unlocks the stories behind song lyrics in various languages, providing insights into the cultural and linguistic diversity of music. Built using Flask, the app integrates with Spotify and potentially YouTube Music, offering features such as lyrics analysis, playlist management, and more, all through an accessible and engaging interface.

## Features

- **Lyrics Analysis**: Analyze lyrics in various languages using the mBERT model.
- **Playlist Management**: Create, organize, and manage your playlists.
- **Spotify Insights**: Get detailed insights on your Spotify account.
- **User Authentication**: Register and sign in to manage your preferences and settings.
- **Responsive Design**: Accessible on desktops, tablets, and mobile devices.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.8 or higher
- Pipenv for dependency management
- Install lib.175.bin https://fasttext.cc/docs/en/language-identification.html

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourgithub/musiclang.git
   ```
2. Navigate to the project directory:
   ```
   cd musiclang
   ```
3. Install dependencies:
   ```
   pipenv install
4. Activate the virtual environment:
   ```
   pipenv shell
   ```
5. Set environment variables. You'll need to create a `.env` file in the root directory of your project and add the following keys:
   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:5000/spotify_callback
   SECRET_KEY=your_secret_key
   GENIUS_ACCESS_TOKEN='your_genius_access_token'
   ```
   Replace the placeholder values with your actual data.
6. Initialize the database:
   ```
   flask db upgrade
   ```
7. Run the application:
   ```
   flask run
   ```

## Usage

Navigate to `http://localhost:5000` in your web browser to start using MusicLang.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.
