import asyncio
import re
from typing import Any, Final

import discord

from chencho_bot.music.models import Track
from chencho_bot.services.spotify import (
    get_album_tracks,
    get_artist_top_tracks,
    get_playlist_tracks,
    get_track_by_url,
    search_track,
)

# Regex para extraer el tipo de recurso y el identificador de Spotify
SPOTIFY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:https?:\/\/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?|spotify:)(track|playlist|album|artist)(?:[:/])([a-zA-Z0-9]+)"
)


class TrackResolver:
    """Resuelve consultas textuales o URLs a entidades de dominio Track."""

    @staticmethod
    def _create_track(track_info: dict[str, Any], requester: discord.Member | None) -> Track:
        search_query = f"{track_info['title']} {track_info['artist']} audio"
        return Track(
            title=track_info["title"],
            artist=track_info["artist"],
            album=track_info.get("album", "Unknown Album"),
            spotify_url=track_info["url"],
            search_query=search_query,
            cover_url=track_info.get("cover_url"),
            duration_ms=track_info.get("duration_ms", 0),
            requester=requester,
        )

    async def resolve(self, query: str, requester: discord.Member | None = None) -> list[Track]:
        query = query.strip()
        match = SPOTIFY_PATTERN.search(query)

        # Si no encaja con ningún patrón de Spotify, se delega a búsqueda textual
        if not match:
            raw = await asyncio.to_thread(search_track, query)
            results = [raw] if raw else []
            return [self._create_track(item, requester=requester) for item in results if item]

        resource_type, resource_id = match.groups()

        if resource_type == "track":
            raw = await asyncio.to_thread(get_track_by_url, query)
            results = [raw] if raw else []

        elif resource_type == "playlist":
            results = await asyncio.to_thread(get_playlist_tracks, query)

        elif resource_type == "album":
            results = await asyncio.to_thread(get_album_tracks, resource_id)

        elif resource_type == "artist":
            results = await asyncio.to_thread(get_artist_top_tracks, resource_id)

        else:
            results = []

        return [self._create_track(item, requester=requester) for item in results if item]
