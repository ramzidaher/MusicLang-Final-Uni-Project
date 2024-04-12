document.addEventListener('DOMContentLoaded', () => {
    const selectPlaylistButton = document.getElementById('selectPlaylistButton');
    const analyzePlaylistButton = document.getElementById('analyzePlaylist');
    const createPlaylistsButton = document.getElementById('createLanguagePlaylistsButton');
    const playlistSelect = document.getElementById('playlistSelect');
    const creationLevelSelect = document.getElementById('creationLevelSelect');
    const tracksContainer = document.getElementById('tracksContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');

    selectPlaylistButton.addEventListener('click', () => {
        const playlistId = playlistSelect.value;
        fetchTracks(playlistId);
    });

    analyzePlaylistButton.addEventListener('click', () => {
        const playlistId = playlistSelect.value;
        if (playlistId) {
            analyzePlaylist(playlistId);
        } else {
            alert('Please select a playlist first.');
        }
    });

    createPlaylistsButton.addEventListener('click', () => {
        const playlistId = playlistSelect.value;
        const level = creationLevelSelect.value;
        if (playlistId) {
            createPlaylists(playlistId, level);
        } else {
            alert('Please select a playlist first.');
        }
    });

    function fetchTracks(playlistId) {
        loadingOverlay.style.display = 'flex';
        fetch(`/api/playlist_tracks/${playlistId}`)
            .then(response => response.json())
            .then(data => displayTracks(data.tracks))
            .catch(error => console.error('Failed to fetch tracks', error))
            .finally(() => loadingOverlay.style.display = 'none');
    }

    function analyzePlaylist(playlistId) {
        loadingOverlay.style.display = 'flex';
        fetch(`/analyze_playlist_languages/${playlistId}`)
            .then(response => response.json())
            .then(data => {
                console.log('Number of tracks analyzed:', data.analysis_results.length); // Add this line
                displayAnalysisResults(data);
            })            .catch(error => console.error('Failed to analyze playlist', error))
            .finally(() => loadingOverlay.style.display = 'none');
    }

    function createPlaylists(playlistId, level) {
        loadingOverlay.style.display = 'flex';
        fetch(`/create_language_playlists/${playlistId}/${level}`)
            .then(response => response.json())
            .then(data => {
                console.log('Number of playlists created:', data.length); // Add this line
                alert('Playlists created successfully!');
                console.log(data);
            })
            .catch(error => {
                console.error('Failed to create playlists', error);
                alert('Failed to create playlists.');
            })
            .finally(() => loadingOverlay.style.display = 'none');
    }

    function displayTracks(tracks) {
        console.log('Number of tracks fetched:', tracks.length); // Add this line
        tracksContainer.innerHTML = '';
        const list = document.createElement('ul');
        tracks.forEach(track => {
            const li = document.createElement('li');
            li.textContent = `${track.name} by ${track.artist}`;
            const lyricsButton = document.createElement('button');
            lyricsButton.textContent = 'Show Lyrics';
            lyricsButton.onclick = () => showLyrics(track.artist, track.name, li);
            li.appendChild(lyricsButton);
            list.appendChild(li);
        });
        tracksContainer.appendChild(list);
    }

    function showLyrics(artist, title, trackElement) {
        // Check if the lyrics div already exists
        let lyricsDiv = trackElement.querySelector('.lyrics');
        if (lyricsDiv) {
            // Toggle the visibility of the lyrics div
            lyricsDiv.style.display = lyricsDiv.style.display === 'none' ? 'block' : 'none';
        } else {
            // If the lyrics div doesn't exist, create it and fetch the lyrics
            lyricsDiv = document.createElement('div');
            lyricsDiv.className = 'lyrics'; // Add a class for styling or referencing
            trackElement.appendChild(lyricsDiv);
            
            fetch(`/api/lyrics?artist=${encodeURIComponent(artist)}&title=${encodeURIComponent(title)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.lyrics) {
                        lyricsDiv.textContent = data.lyrics;
                    } else {
                        lyricsDiv.textContent = 'Lyrics not found.';
                    }
                    lyricsDiv.style.display = 'block'; // Ensure it's visible after fetching
                }).catch(error => {
                    console.error('Error fetching lyrics:', error);
                    lyricsDiv.textContent = 'Failed to fetch lyrics.';
                    lyricsDiv.style.display = 'block'; // Ensure it's visible even on error
                });
        }
    }
    

    function displayAnalysisResults(data) {
        tracksContainer.innerHTML = '';
        const list = document.createElement('ul');
        data.analysis_results.forEach(result => {
            const li = document.createElement('li');
            li.textContent = `${result.track_name} by ${result.artist_name}: ${result.languages.map(lang => `${lang[0]} (${lang[1]}%)`).join(', ')}`;
            list.appendChild(li);
        });
        tracksContainer.appendChild(list);

        // Display average language distribution if available
        if (data.average_languages) {
            const languagesContainer = document.createElement('div');
            languagesContainer.classList.add('languages');

            const heading = document.createElement('h2');
            heading.textContent = 'Average Language Distribution in Playlist';
            heading.className = 'centered-heading';
            languagesContainer.appendChild(heading);

            const sortedLanguages = Object.entries(data.average_languages).sort((a, b) => b[1] - a[1]);
            sortedLanguages.forEach(([lang, percentage]) => {
                const span = document.createElement('span');
                span.classList.add('language');
                span.textContent = `${lang}: ${percentage.toFixed(2)}%`;
                languagesContainer.appendChild(span);
            });

            tracksContainer.appendChild(languagesContainer);
        }
    }
});