import asyncio
import logging

import discord

from chencho_bot.music.models import Track
from chencho_bot.music.queue import MusicQueue
from chencho_bot.services.audio import get_audio_stream
from chencho_bot.utils.embeds import build_now_playing_embed
from chencho_bot.utils.view import PlayerControlsView

logger = logging.getLogger(__name__)

FFMPEG_OPTIONS = {
    "before_options": (
        "-nostdin "
        "-loglevel quiet "
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-reconnect_on_network_error 1 "
        "-analyzeduration 0 "
        "-probesize 32k"
    ),
    "options": "-vn -ar 48000 -ac 2",
}


class MusicPlayer:
    """Gestiona la reproducción musical de un servidor."""

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.queue = MusicQueue()
        self.voice_client: discord.VoiceClient | None = None
        self.text_channel: discord.abc.Messageable | None = None

        self.current_track: Track | None = None
        self._play_previous = False
        self._manual_stop = False
        self._play_lock = asyncio.Lock()

    @property
    def is_playing(self) -> bool:
        """Determina si el reproductor tiene audio activo o en pausa."""
        if not self.voice_client or not self.voice_client.is_connected():
            return False
        return self.voice_client.is_playing() or self.voice_client.is_paused()

    @property
    def is_paused(self) -> bool:
        """Indica si la reproducción está pausada."""
        return bool(self.voice_client and self.voice_client.is_paused())

    async def play_next(self) -> None:
        """Obtiene y reproduce la siguiente canción."""
        async with self._play_lock:
            await self._play_next()

    async def _play_next(self) -> None:
        logger.debug(
            "[bold cyan][PLAYER][/bold cyan] Entrando a _play_next | current_track=%s, queue_empty=%s",  # noqa: E501
            self.current_track,
            self.queue.is_empty(),
        )
        logger.debug(
            "[bold cyan][PLAYER][/bold cyan] Canciones en cola: [magenta]%s[/magenta]",
            len(self.queue.get_tracks()),
        )

        # Guarda de conexión
        if self.voice_client is None or not self.voice_client.is_connected():
            return

        # Guarda de reproducción activa
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            logger.debug(
                "[bold yellow][PLAYER][/bold yellow] Ya hay audio reproduciéndose o pausado. Cancelando _play_next()."
            )
            return

        if self._manual_stop:
            self._manual_stop = False
            return

        # 1. Determinar qué canción reproducir
        if self._play_previous:
            track = self.current_track
            self._play_previous = False
        elif self.current_track and self.current_track.loop:
            track = self.current_track
        else:
            if self.queue.is_empty():
                self.current_track = None
                return
            track = self.queue.get_next()

        if track is None:
            return

        self.current_track = track

        # 2. Obtener el stream de audio
        audio_data = await get_audio_stream(track.search_query)

        if not audio_data or "url" not in audio_data:
            await self._notify(
                f"No se pudo cargar el audio para: **{track.title}**. Saltando..."
            )
            self.current_track = None
            await self.play_next()
            return

        track.audio_stream_url = audio_data["url"]

        # 3. Crear el reproductor FFmpeg
        source = discord.FFmpegPCMAudio(
            track.audio_stream_url,
            **FFMPEG_OPTIONS,
        )

        # 4. Callback cuando termina la canción
        def after_playback(error: Exception | None) -> None:
            if error:
                logger.error("[bold red][FFMPEG ERROR][/bold red] %s", error)

            asyncio.run_coroutine_threadsafe(
                self.play_next(),
                self.bot.loop,
            )

        # 5. Reproducir
        self.voice_client.play(
            source,
            after=after_playback,
        )

        # 6. Notificar al canal
        if self.text_channel and self.current_track:
            embed = build_now_playing_embed(self.current_track)
            view = PlayerControlsView(player=self)

            await self.text_channel.send(
                embed=embed,
                view=view,
            )

    async def _notify(self, message: str) -> None:
        """Envía un mensaje al canal de texto asociado."""
        if self.text_channel:
            await self.text_channel.send(message)

    def pause(self) -> bool:
        """Pausa la reproducción actual."""
        if self.is_playing:
            self.voice_client.pause()
            return True
        return False

    def resume(self) -> bool:
        """Reanuda la reproducción pausada."""
        if self.is_paused:
            self.voice_client.resume()
            return True
        return False

    def skip(self) -> bool:
        """Detiene la canción actual y continúa con la siguiente."""
        if self.voice_client is None:
            return False

        if self.is_playing or self.is_paused:
            self._manual_stop = False
            self.voice_client.stop()
            return True

        return False

    def stop(self) -> None:
        """Detiene la reproducción y limpia la cola."""
        self._manual_stop = True
        self._play_previous = False

        self.queue.clear()
        self.current_track = None

        if self.voice_client is not None and (self.is_playing or self.is_paused):
            self.voice_client.stop()

    def previous(self) -> bool:
        """Reproduce la canción anterior."""
        if self.voice_client is None or not self.queue.has_previous():
            return False

        previous_track = self.queue.get_previous(self.current_track)
        if previous_track is None:
            return False

        self.current_track = previous_track
        self._play_previous = True
        self._manual_stop = False

        if self.is_playing or self.is_paused:
            self.voice_client.stop()
        else:
            asyncio.create_task(self.play_next())

        return True

    def loop(self) -> bool:
        """Alterna el modo de repetición de la canción actual."""
        if self.current_track is None:
            return False

        self.current_track.loop = not self.current_track.loop
        return self.current_track.loop
