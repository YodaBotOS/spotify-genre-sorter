# Spotify Music Genre
This repo uses Python with the Spotify API and OAuth2 to generate a playlist of songs based on the genre and creates a new playlist for that specific genre.

# ⚠️ WARNING ⚠️
This project is still a Work In Progress, which means there will be a lot of bugs and unexpected things.

Feel free to experiment with this repo and [report any issues](https://github.com/OpenRobot/spotify-music-genre/issues) you find.

[PRs](https://github.com/OpenRobot/spotify-music-genre/pulls) are always welcomed.

# Credits:
This is taken from [GitHub (@cetinsamet/music-genre-classification)](https://github.com/cetinsamet/music-genre-classification)

All credits go to him for making this amazing repo possible.

# Setup:
The below steps assumed you already have fulfilled the following requirements:
- You have installed Python3.10 or above with pip in your computer. 
- You have [Git](https://git-scm.com/) installed in your computer. (Most OS comes with git built in, especially Linux distros)
- [A Spotify API Client ID and Secret](https://developer.spotify.com)

1. Clone this repository (it might take some time depending on your internet speed).
```shell
git clone https://github.com/OpenRobot/spotify-music-genre
```
2. Install the required dependencies (Note. It is recommended to use a [venv](https://docs.python.org/3/library/venv.html) instead).
```shell
pip install -U -r requirements.txt
```
3. Copy `config.example.py` to the root folder of the repository, named `config.py`.
4. Insert all the values for the essential variables. This includes:
    - SPOTIFY_PLAYLIST_ID
    - SPOTIFY_CLIENT_ID
    - SPOTIFY_CLIENT_SECRET
    - SPOTIFY_REDIRECT_URI
5. Run the script.
```shell
python3 main.py
```
6. Follow the instructions in your terminal.