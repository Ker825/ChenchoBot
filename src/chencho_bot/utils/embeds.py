import discord

from chencho_bot.music.queue import Track


def build_added_track_embed(track: Track, position: int) -> discord.Embed:
    """Construye el embed de confirmacion al encolar una pista."""
    minutos = track.duration_ms // 60000
    segundos = (track.duration_ms % 60000) // 1000
    duracion = f"{minutos:02d}:{segundos:02d}"

    embed = discord.Embed(color=discord.Color.green())

    embed.set_author(
        name="Added Track",
        icon_url="https://cdn.discordapp.com/attachments/1555860094980325447/1556029525396033617/IconoBot.jpg?backend=b2&ex=6ac2acec&is=6ac15b6c&hm=68e30f320c74a603bbada2cfff0e1d35fbe9788e2bf1c0da5290c3723b6e20ca&",
    )

    embed.description = (
        f"**Track**\n[{track.title} by {track.artist}]({track.spotify_url})"
    )

    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    embed.add_field(name="Track Length", value=duracion, inline=True)
    embed.add_field(name="Position in queue", value=str(position), inline=True)

    if track.requester:
        embed.set_footer(
            text=f"Requested by {track.requester.display_name}",
            icon_url=(
                track.requester.display_avatar.url
                if track.requester.display_avatar
                else None
            ),
        )

    return embed


def build_now_playing_embed(track: Track, current_ms: int = 0) -> discord.Embed:
    embed = discord.Embed(color=discord.Color.green())

    embed.set_author(
        name="Now Playing",
        icon_url="https://cdn.discordapp.com/attachments/1555860094980325447/1556029525396033617/IconoBot.jpg?backend=b2&ex=6ac2acec&is=6ac15b6c&hm=68e30f320c74a603bbada2cfff0e1d35fbe9788e2bf1c0da5290c3723b6e20ca&",
    )

    progress_line = generate_progress_bar(current_ms, track.duration_ms)

    embed.description = (
        f"**Track**\n"
        f"[{track.title} by {track.artist}]({track.spotify_url})\n\n"
        f"{progress_line}"
    )

    if track.cover_url:
        embed.set_thumbnail(url=track.cover_url)

    if track.requester:
        avatar = (
            track.requester.display_avatar.url
            if track.requester.display_avatar
            else None
        )
        embed.set_footer(
            text=f"Requested by {track.requester.display_name}",
            icon_url=avatar,
        )

    return embed


def format_time(ms: int) -> str:
    """Convierte milisegundos a formato MM:SS."""
    seconds = max(0, ms // 1000)
    minutes = seconds // 60
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:02d}"


def generate_progress_bar(current_ms: int, total_ms: int, bar_length: int = 10) -> str:
    """Genera una barra de progreso textual estilo reproductor."""
    if total_ms <= 0:
        bar = "─" * bar_length
        return f"00:00 {bar} 00:00"

    progress = min(max(current_ms / total_ms, 0.0), 1.0)
    pos = int(progress * (bar_length - 1))

    bar = f"{'━' * pos}●{'─' * (bar_length - 1 - pos)}"
    elapsed = format_time(current_ms)
    remaining = f"-{format_time(total_ms - current_ms)}"

    return f"`{elapsed}` {bar} `{remaining}`"
