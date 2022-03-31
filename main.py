import os
import sys
import json
import asyncio
import subprocess

import config
import spotify
from utils import *

check = check_imports()

if check[0] is False:
    raise ImportError(f'Library {check[1].name} is not installed. Please install all the required libraries from '
                      f'"requirements.txt" file by doing "pip install -r requirements.txt" or similar.') from None

print("[+] Starting...")

print("[+] Checking for updates...")

process = subprocess.Popen(["git", "pull"])
stdout, stderr = process.communicate()

if stdout.decode('utf-8') == "Already up to date." or stdout.decode('utf-8') == "Already up to date.":
    pass
else:
    print("[+] Update successful!")
    print("[+] Restarting... Please start the program again.")

    os._exit(0)

print("[+] Starting webserver...")

print("-" * 25)
print("Make sure to sign-in using the user that you want to use to add the playlists.")
print("Note that this software only supports public playlists. This software does not work for private playlists nor "
      "liked songs.")

status_code = os.system(sys.executable + os.path.dirname(os.path.abspath(__file__)) + "/webserver.py")

if status_code != 0:  # Exited abnormally
    print("[-] Webserver exited abnormally. Please try again. If this is a bug, please submit an issue on GitHub, "
          "https://github.com/OpenRobot/spotify-music-genre")
    os._exit(1)

print("[+] Spotify Track WebServer has been stopped")

with open("request.json", "r") as f:
    js_callback = json.load(f)

code = js_callback["code"]
state = js_callback["state"]

with open("request.json", "w") as f:
    json.dump({}, f)

print("[+] Request.json has been cleared")

print("[+] Requesting for a Access Token from Spotify")


async def coro():
    async with spotify.Client(config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET) as client:
        try:
            await client.requesst_access_token(code, config.SPOTIFY_REDIRECT_URI, renew=True)

            print(f"[+] Getting User information...")

            user = await client.get_user_info()

            confirm_user = input(f"Are you sure that you want to add the Genre playlists on {user.display_name} "
                                 f"{user.external_urls['spotify']} [Y/n] ")

            while True:
                if confirm_user.lower() in ['', 'y', 'yes']:
                    break
                elif confirm_user.lower() in ['n', 'no']:
                    print("[+] Exiting...")
                    os._exit(0)
                else:
                    confirm_user = input("Please enter 'Y' or 'N' as your answer: ")

            print("[+] Logged in as User: {} | {}".format(user.display_name, user.external_urls['spotify']))

            # print("[+] Getting all track in the playlist")
            #
            # offset = 0
            #
            # tracks = []
            #
            # while True:
            #     response_tracks = await client.get_playlist_items(config.SPOTIFY_PLAYLIST_ID,
            #                                                       offset=offset, limit=100)
            #
            #     if not response_tracks.items:
            #         break
            #
            #     tracks += [x['track'] for x in response_tracks.items]
            #
            #     offset += 100
            #
            # print(f"[+] Tracks have been retrieved. There are {len(tracks)} tracks in the playlist.")

            print("[+] Running Music Genre Classification")

            # async def pre_genre_classification():
            #     genres_classification = []
            #
            #     for track in tracks:
            #         await run_genre_classification(track)
            #
            # asyncio.create_task(pre_genre_classification())

            await check_new_tracks(client)
        finally:  # Avoiding memory leaks and KeyboardInterrupts.
            await client.close()


asyncio.run(coro())
