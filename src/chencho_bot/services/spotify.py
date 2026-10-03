import re
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from chencho_bot.config.settings import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
)

spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-read-private playlist-read-collaborative",
    )
)


def _format_track(
    data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Convierte un track de Spotify a nuestro formato."""

    if not data or not data.get("name"):
        return None

    artists = ", ".join(artist["name"] for artist in data.get("artists", []))

    album_data = data.get("album", {})
    images = album_data.get("images", [])

    return {
        "title": data.get("name", "Desconocido"),
        "artist": artists,
        "album": album_data.get("name", ""),
        "url": data.get("external_urls", {}).get(
            "spotify",
            "",
        ),
        "cover_url": (images[0]["url"] if images else None),
        "duration_ms": data.get(
            "duration_ms",
            0,
        ),
    }


def search_track(
    query: str,
) -> dict[str, Any] | None:
    """Busca una canción por texto."""

    results = spotify.search(
        q=query,
        limit=1,
        type="track",
    )

    items = results.get(
        "tracks",
        {},
    ).get(
        "items",
        [],
    )

    if not items:
        return None

    return _format_track(items[0])


def get_track_by_url(
    url: str,
) -> dict[str, Any] | None:
    """Obtiene una canción mediante su URL de Spotify."""

    match = re.search(
        r"track/([a-zA-Z0-9]+)",
        url,
    )

    if not match:
        return None

    try:
        data = spotify.track(match.group(1))

        return _format_track(data)

    except Exception as error:
        print(f"Error obteniendo track por URL: {error}")
        return None


def get_playlist_tracks(
    url: str,
) -> list[dict[str, Any]]:
    """Obtiene todas las canciones de una playlist de Spotify."""

    match = re.search(
        r"playlist/([a-zA-Z0-9]+)",
        url,
    )

    if not match:
        return []

    playlist_id = match.group(1)
    tracks: list[dict[str, Any]] = []

    offset = 0
    limit = 100

    try:
        while True:
            results = spotify.playlist_items(
                playlist_id,
                offset=offset,
                limit=limit,
                additional_types=("track",),
            )

            items = results.get(
                "items",
                [],
            )

            if not items:
                break

            for item in items:
                # La clave en este endpoint es 'item', con fallback a 'track'
                track_data = item.get("item") or item.get("track")
                formatted = _format_track(track_data)

                if formatted:
                    tracks.append(formatted)

            offset += len(items)

            if results.get("next") is None:
                break

        return tracks

    except Exception as error:
        print(f"Error obteniendo tracks de playlist: {error}")

        return []
