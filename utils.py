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


def remove_tmp():
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    tmp_path = current_file_path + "/tmp/"

    for file in os.listdir(tmp_path):
        os.remove(tmp_path + file)

    os.rmdir(tmp_path)


async def get_available(client: spotify.Client) -> tuple[dict[str, dict], dict[str, dict[spotify.Track, list[int]]]]:
    tracks_available = {
        'playlist-track': {},
        # 'track-playlist': [],
    }

    playlists = []
    offset = 0

    user = await client.get_user_info()

    while True:
        response = await client.user_playlists(limit=50, offset=offset)

        if not response.items:
            break

        playlists += response.items

        offset += response.limit

    _available_playlists = [x for x in playlists if x['owner']['id'] == user.id and x['name'] in [
        config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre.title())) for genre in
        ['blues', 'classical', 'country', 'disco', 'hiphop', 'jazz', 'metal', 'pop', 'reggae', 'rock']
    ]]

    available_playlists = {}

    for i in _available_playlists:
        for genre in ['blues', 'classical', 'country', 'disco', 'hiphop', 'jazz', 'metal', 'pop', 'reggae', 'rock']:
            if config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre.title())) == i[
                'name']:
                available_playlists[genre] = i

    for genre, playlist in available_playlists.items():
        offset = 0

        tracks = []

        playlist_id = playlist['id']

        while True:
            response_tracks = await client.get_playlist_items(playlist_id, offset=offset, limit=100)

            if not response_tracks.items:
                break

            tracks += [x['track'] for x in response_tracks.items]

            offset += response.limit

        tracks_available['playlist-track'][playlist_id] = tracks

        added_playlist_ids = {}

        # for track in tracks:
        #     if {'track': track, 'playlist_ids': added_playlist_ids} in tracks_available['track-playlist']:
        #         #tracks_available['track-playlist'][track].append(playlist_id)
        #         tracks_available['track-playlist'][tracks_available['track-playlist'].index(
        #             {'track': track, 'playlist_ids': added_playlist_ids})]['playlist_ids'].append(playlist_id)
        #     else:
        #         tracks_available['track-playlist'].append({
        #             'track': track,
        #             'playlist_ids': [playlist_id]
        #         })
        #
        #     if track.id in added_playlist_ids:
        #         added_playlist_ids[track.id].append(playlist_id)
        #     else:
        #         added_playlist_ids[track.id] = [playlist_id]

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
                               f"cd {cwd}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    stdout, stderr = process.communicate()

    os.remove(track_path)

    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')

    output = stdout + stderr

    genres = {}

    # print("stdout: ", stdout)
    # print("stderr: ", stderr)

    for line in output.split("\n"):
        if not line:
            continue

        genre, confidence = line.split(":")
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
        # print(1)
        offset = 0

        tracks = []

        while True:
            response_tracks = await client.get_playlist_items(config.SPOTIFY_PLAYLIST_ID, offset=offset, limit=100)

            if not response_tracks.items:
                break

            tracks += [x['track'] for x in response_tracks.items]

            offset += response_tracks.limit

        # print(2)

        available_playlists, tracks_available = await get_available(client)

        # print(3)

        # if tracks_before:
        #     removed_tracks = handle_removed_tracks(tracks, tracks_before)

        for playlist, playlist_tracks in tracks_available['playlist-track'].items():
            # to_be_removed = []
            #
            # for track in tracks_available['playlist-track'][playlist]:
            #     if track in removed_tracks:
            #         to_be_removed.append(track)
            #
            # # print(to_be_removed)
            #
            # await client.remove_playlist_tracks(playlist, to_be_removed)

            to_be_removed = []

            for playlist_track in playlist_tracks:
                if playlist_track not in tracks:
                    to_be_removed.append(playlist_track)

            # print(playlist, to_be_removed)

            if not to_be_removed:
                continue

            # print("debug yes")

            await client.remove_playlist_tracks(playlist, to_be_removed)

        # ----------------------------------------------------------------- #

        # print(4, tracks)

        genre_tracks = {}

        for track in tracks:
            if track in tracks_before:
                continue

            try:
                genres = await run_genre_classification(track)
            except Exception as e:
                raise e

            # print(5)

            for genre, confidence in genres.items():
                if not genre or not confidence or genre.lower() in [x.lower() for x in config.GENRES_IGNORED]:
                    continue

                if genre not in genre_tracks:
                    genre_tracks[genre] = []

                genre_tracks[genre].append({
                    'track': track,
                    'confidence': confidence,
                })

            # print(6)

        for genre in genre_tracks:
            if genre not in available_playlists:
                playlist_created = False
                # description = config.GENRE_DEFAULT_PLAYLIST_DESCRIPTION or ''
                # playlist = await client.create_playlist(
                #     config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre.title())),
                #     description=config.GENRE_PLAYLIST_DESCRIPTION.get(
                #         genre, description.format(genre.title())
                #     ) or None,
                #     public=config.GENRE_PLAYLIST_PUBLIC.get(genre, config.GENRE_DEFAULT_PLAYLIST_PUBLIC),
                # )
                # playlist_id = playlist.id
            else:
                playlist_created = True
                playlist_id = available_playlists[genre]['id']

            # print(7)

            offset = 0
            tracks = []

            if playlist_created is True:
                while True:
                    response_tracks = await client.get_playlist_items(playlist_id, offset=offset, limit=100)

                    if not response_tracks.items:
                        break

                    tracks += [x['track'] for x in response_tracks.items]

                    offset += response_tracks.limit

            # print(8)

            # print(tracks)

            tracks_to_add = [x['track'] for x in genre_tracks[genre] if x['track'] not in tracks]

            # print(tracks_to_add)

            if not tracks_to_add:
                continue

            if playlist_created is False:
                description = config.GENRE_DEFAULT_PLAYLIST_DESCRIPTION or ''
                playlist = await client.create_playlist(
                    config.GENRE_PLAYLIST_NAME.get(genre, config.GENRE_DEFAULT_PLAYLIST_NAME.format(genre.title())),
                    description=config.GENRE_PLAYLIST_DESCRIPTION.get(
                        genre, description.format(genre.title())
                    ) or None,
                    public=config.GENRE_PLAYLIST_PUBLIC.get(genre, config.GENRE_DEFAULT_PLAYLIST_PUBLIC),
                )
                playlist_id = playlist.id

            # print(9)

            await client.add_playlist_tracks(playlist_id, tracks_to_add)

            print(f"[LOGS] Added tracks {tracks_to_add} to {playlist_id}")

            # print(10)

            await asyncio.sleep(1.5)

        tracks_before = tracks

        # print(11)

        await asyncio.sleep(5)
