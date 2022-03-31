import os
import asyncio
import subprocess

import aiohttp

import config
import spotify


def check_imports() -> tuple[bool, ImportError | None]:
    try:
        import numpy
        import torch
        import sklearn
        import librosa
        import pandas
        import aiohttp
        import fastapi
        import uvicorn
    except ImportError as e:
        return False, e
    else:
        return True, None


async def get_available(client: spotify.Client) -> tuple[dict[str, dict], dict[str, dict[spotify.Track, list[int]]]]:
    tracks_available = {
        'playlist-track': {},
        'track-playlist': {},
    }

    playlists = []
    offset = 0

    user = await client.get_user_info()

    while True:
        response = await client.user_playlists(limit=100, offset=offset)

        if not response.items:
            break

        playlists += response.items

        offset += response.limit

    _available_playlists = [x for x in playlists if x['owner']['id'] == user.id and x['name'] in [
        config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre)) for genre in
        ['blues', 'classical', 'country', 'disco', 'hiphop', 'jazz', 'metal', 'pop', 'reggae', 'rock']
    ]]

    available_playlists = {}

    for i in _available_playlists:
        for genre in ['blues', 'classical', 'country', 'disco', 'hiphop', 'jazz', 'metal', 'pop', 'reggae', 'rock']:
            if config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre)) == i['name']:
                available_playlists[genre] = i

    for playlist_id in available_playlists:
        offset = 0

        tracks = []

        while True:
            response_tracks = await client.get_playlist_items(playlist_id, offset=offset, limit=100)

            if not response_tracks.items:
                break

            tracks += [x['track'] for x in response_tracks.items]

            offset += response.limit

        tracks_available['playlist-track'][playlist_id] = tracks

        for track in tracks:
            if track in tracks_available['track-playlist']:
                tracks_available['track-playlist'][track].append(playlist_id)
            else:
                tracks_available['track-playlist'][track] = [playlist_id]

    return available_playlists, tracks_available


async def run_genre_classification(track: spotify.Track) -> dict[str, float]:
    cwd = os.getcwd()
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    tmp_path = current_file_path + "/tmp/"

    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)

    async with aiohttp.ClientSession() as session:
        async with session.get(track.preview_url) as resp:
            track_path = tmp_path + track.id + ".mp3"

            with open(track_path, "wb") as fp:
                fp.write(await resp.read())

    # "cd " + os.path.dirname(os.path.abspath(__file__)) + "music-genre-classification/src" + f" && python3
    # get_genre.py {track_path}"

    process = subprocess.Popen(f"cd {os.path.dirname(os.path.abspath(__file__))}/music-genre-classification/src && "
                               f"python3 get_genre.py {track_path} && "
                               f"cd {cwd}")

    stdout, stderr = process.communicate()

    os.remove(track_path)

    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')

    output = stdout + stderr

    genres = {}

    for line in output.split("\n"):
        for genre, confidence in line.split(":"):
            genres[genre.strip()] = float(confidence.strip())

    return genres


def handle_removed_tracks(tracks: list[spotify.Track], tracks_before: list[spotify.Track]) -> list[spotify.Track]:
    # returns the removed tracks
    removed_tracks = []

    for track in tracks_before:
        # if track not in tracks and (track in tracks_before or track in tracks_available['track-playlist'])
        if track in tracks_before and track not in tracks:
            removed_tracks.append(track)

    return removed_tracks


async def check_new_tracks(client: spotify.Client, *, tracks_before: list[spotify.Track] = None):
    tracks_before = tracks_before or []

    while True:
        offset = 0

        tracks = []

        while True:
            response_tracks = await client.get_playlist_items(config.SPOTIFY_PLAYLIST_ID, offset=offset, limit=100)

            if not response_tracks.items:
                break

            tracks += [x['track'] for x in response_tracks.items]

            offset += response_tracks.limit

        available_playlists, tracks_available = await get_available(client)

        if tracks_before:
            removed_tracks = handle_removed_tracks(tracks, tracks_before)

            for playlist in tracks_available['playlist-track']:
                to_be_removed = []

                for track in tracks_available['playlist-track'][playlist]:
                    if track in removed_tracks:
                        to_be_removed.append(track)

                await client.remove_playlist_tracks(playlist, to_be_removed)

        genre_tracks = {}

        for track in tracks:
            if track in tracks_before:
                continue

            try:
                genres = await run_genre_classification(track)
            except:
                continue

            for genre, confidence in genres.items():
                if not genre or not confidence or genre.lower() in [x.lower() for x in config.GENRES_IGNORED]:
                    continue

                if genre not in genre_tracks:
                    genre_tracks[genre] = []

                genre_tracks[genre].append({
                    'track': track,
                    'confidence': confidence,
                })

        for genre in genre_tracks:
            if genre not in available_playlists:
                playlist = await client.create_playlist(
                    config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre)),
                    description=config.GENRE_PLAYLIST_DESCRIPTION.get(
                        genre, config.GENRE_DEFAULT_PLAYLIST_DESCRIPTION.format(genre)
                    ) or None,
                    public=config.GENRE_PLAYLIST_PUBLIC.get(genre, config.GENRE_DEFAULT_PLAYLIST_PUBLIC),
                )
                playlist_id = playlist.id
            else:
                playlist_id = available_playlists[genre]['id']

            offset = 0
            tracks = []

            while True:
                response_tracks = await client.get_playlist_items(config.SPOTIFY_PLAYLIST_ID, offset=offset, limit=100)

                if not response_tracks.items:
                    break

                tracks += [x['track'] for x in response_tracks.items]

                offset += response_tracks.limit

            tracks_to_add = [x['track'] for x in genre_tracks[genre]]

            for i in tracks_to_add:
                if i in tracks:
                    tracks_to_add.remove(i)

            await client.add_playlist_tracks(playlist_id, tracks_to_add)

            await asyncio.sleep(1.5)

        tracks_before = tracks

        await asyncio.sleep(3)
