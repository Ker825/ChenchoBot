from dataclasses import dataclass

import discord


@dataclass
class Track:
    """Representa una canción que puede ser reproducida."""

    title: str
    artist: str
    album: str | None
    spotify_url: str
    search_query: str

    # Se obtiene justo antes de reproducir.
    audio_stream_url: str = ""

    cover_url: str | None = None
    duration_ms: int = 0
    requester: discord.Member | None = None
    loop: bool = False
