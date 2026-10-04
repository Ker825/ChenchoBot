import math
from typing import Final

import discord

from chencho_bot.music.models import Track

# Constantes de identidad visual
COLOR_PRIMARY: Final[int] = 0x1DB954  # Verde Spotify
COLOR_NEUTRAL: Final[int] = 0x2B2D31  # Gris oscuro Discord
COLOR_ERROR: Final[int] = 0xFF0000  # Rojo
BOT_ICON_URL: Final[str] = "https://cdn.discordapp.com/attachments/1555860094980325447/1556029525396033617/IconoBot.jpg"


def format_time(ms: int) -> str:
    """Convierte milisegundos a una cadena con formato MM:SS o HH:MM:SS."""
    if ms <= 0:
        return "00:00"

    total_seconds = ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def generate_progress_bar(
    current_ms: int,
    total_ms: int,
    bar_length: int = 10,
) -> str:
    """Genera una barra de progreso textual para el reproductor."""
    safe_bar_length = max(3, bar_length)

    if total_ms <= 0:
        bar = "\u2500" * safe_bar_length
        return f"`00:00` {bar} `00:00`"

    clamped_current = min(max(current_ms, 0), total_ms)
    progress = clamped_current / total_ms
    pos = int(progress * (safe_bar_length - 1))

    # Secuencias Unicode para evitar emojis literales
    filled_part = "\u2501" * pos
    indicator = "\u25cf"
    unfilled_part = "\u2500" * (safe_bar_length - 1 - pos)

    bar = f"{filled_part}{indicator}{unfilled_part}"
    elapsed = format_time(clamped_current)
    remaining = f"-{format_time(total_ms - clamped_current)}"

    return f"`{elapsed}` {bar} `{remaining}`"


def _apply_requester_footer(embed: discord.Embed, track: Track) -> None:
    """Aplica el pie de pagina diferenciando si fue pedida por un usuario o por Autoplay."""
    if not track.requester:
        embed.set_footer(
            text="Recomendado automaticamente por Autoplay (YouTube Music)",
            icon_url=BOT_ICON_URL,
        )
        return

    avatar_url = (
        track.requester.display_avatar.url
        if hasattr(track.requester, "display_avatar") and track.requester.display_avatar
        else None
    )
    embed.set_footer(
        text=f"Requested by {track.requester.display_name}",
        icon_url=avatar_url,
    )


def build_searched_track_embed(track: Track) -> discord.Embed:
    """Construye el embed informativo al buscar una pista individual."""
    embed = discord.Embed(color=COLOR_PRIMARY)
    embed.set_author(name="Searched Track", icon_url=BOT_ICON_URL)
    embed.description = f"**Track**\n[{track.title} by {track.artist}]({track.spotify_url})"

    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    embed.add_field(
        name="Track Length",
        value=format_time(track.duration_ms),
        inline=True,
    )
    _apply_requester_footer(embed, track)
    return embed


def build_added_track_embed(track: Track, position: int) -> discord.Embed:
    """Construye el embed de confirmacion al encolar una pista."""
    embed = discord.Embed(color=COLOR_PRIMARY)
    embed.set_author(name="Added Track", icon_url=BOT_ICON_URL)
    embed.description = f"**Track**\n[{track.title} by {track.artist}]({track.spotify_url})"

    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    embed.add_field(name="Track Length", value=format_time(track.duration_ms), inline=True)
    embed.add_field(name="Position in queue", value=str(position), inline=True)

    _apply_requester_footer(embed, track)
    return embed


def build_now_playing_embed(track: Track, current_ms: int = 0) -> discord.Embed:
    """Construye la tarjeta activa distinguiendo canciones de Autoplay."""
    embed = discord.Embed(color=COLOR_PRIMARY)

    # Identificador de origen en el encabezado
    author_name = "Now Playing • Autoplay" if track.requester is None else "Now Playing"
    embed.set_author(name=author_name, icon_url=BOT_ICON_URL)

    progress_line = generate_progress_bar(current_ms, track.duration_ms)
    embed.description = f"**Track**\n[{track.title} by {track.artist}]({track.spotify_url})\n\n{progress_line}"

    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    _apply_requester_footer(embed, track)
    return embed


def build_queue_page_embed(
    tracks: list[Track],
    current_page: int,
    per_page: int = 10,
) -> discord.Embed:
    """Construye el embed paginado de la lista de reproduccion."""
    total_tracks = len(tracks)
    safe_per_page = max(1, per_page)
    total_pages = max(1, math.ceil(total_tracks / safe_per_page))
    page = max(1, min(current_page, total_pages))

    start_idx = (page - 1) * safe_per_page
    end_idx = start_idx + safe_per_page
    page_tracks = tracks[start_idx:end_idx]

    embed = discord.Embed(
        title="Cola de Reproduccion",
        color=COLOR_PRIMARY,
    )

    if not page_tracks:
        embed.description = "No hay canciones en espera."
        return embed

    lines = [
        f"`{idx}.` **{t.title}** - {t.artist} `[{format_time(t.duration_ms)}]`"
        for idx, t in enumerate(page_tracks, start=start_idx + 1)
    ]

    total_duration_ms = sum(t.duration_ms for t in tracks if t.duration_ms > 0)
    embed.description = "\n".join(lines)
    embed.set_footer(
        text=(
            f"Pagina {page}/{total_pages} | "
            f"Total: {total_tracks} canciones | "
            f"Duracion estimada: {format_time(total_duration_ms)}"
        )
    )
    return embed


def build_status_embed(
    message: str,
    success: bool = True,
) -> discord.Embed:
    """Construye un embed compacto de estado o confirmacion de accion."""
    color = COLOR_PRIMARY if success else COLOR_ERROR
    return discord.Embed(
        description=message,
        color=color,
    )
