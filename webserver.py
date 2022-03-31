import os
import json

import uvicorn
import fastapi
import config
from fastapi.responses import RedirectResponse as redirect

app = fastapi.FastAPI(title="Spotify Music Genre", version="0", openapi_url=None, docs_url=None, redoc_url=None)

spotify_uri = 'https://accounts.spotify.com/authorize?client_id=%s&response_type=code&redirect_uri=%s&scope=%s'

@app.get("/")
async def root():
    scopes = '%20'.join(config.SPOTIFY_SCOPES)
    uri = spotify_uri % (config.SPOTIFY_CLIENT_ID, config.SPOTIFY_REDIRECT_URI, scopes)

    if getattr(config, 'SPOTIFY_STATE', None):
        uri += '&state=%s' % config.SPOTIFY_STATE

    return redirect(uri)

@app.get("/callback")
async def callback(code: str, state: str):
    js = {'code': code, 'state': state}

    with open('request.json', 'w') as f:
        json.dump(js, f)

    os._exit(0)

def run():
    uvicorn.run(app, **config.WEBSERVER_RUN_CONFIG)

run()