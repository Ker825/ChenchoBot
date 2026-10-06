import asyncio
import logging

import discord

from chencho_bot.music.events import PlayerEventListener
from chencho_bot.music.models import Track
from chencho_bot.music.queue import MusicQueue
from chencho_bot.services.audio import get_audio_stream
from chencho_bot.services.yt_recommendations import YouTubeMusicRecommender

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
}


class MusicPlayer:
    """Gestiona el estado, transformacion de volumen y ciclo de vida de reproduccion de audio."""

    def __init__(
        self,
        bot: discord.Client,
        listener: PlayerEventListener | None = None,
    ) -> None:
        self.bot = bot
        self.listener = listener
        self.queue = MusicQueue()
        self.voice_client: discord.VoiceClient | None = None

        self.current_track: Track | None = None
        self._play_previous = False
        self._manual_stop = False
        self._play_lock = asyncio.Lock()
        self._move_current = False
        self._next_track: Track | None = None

        self.autoplay: bool = True
        self.volume: int = 100
        self.recommender = YouTubeMusicRecommender()

        # Watchdog de reproduccion
        self._playback_watchdog_task: asyncio.Task | None = None

        # Temporizadores de ciclo de vida
        self._timeout_task: asyncio.Task | None = None
        self._timeout_seconds: int = 180
        self._empty_channel_task: asyncio.Task | None = None
        self._empty_grace_seconds: int = 60

    @property
    def is_playing(self) -> bool:
        if not self.voice_client or not self.voice_client.is_connected():
            return False

        return self.voice_client.is_playing() or self.voice_client.is_paused()

    @property
    def is_paused(self) -> bool:
        return bool(self.voice_client and self.voice_client.is_paused())

    def set_volume(self, volume: int) -> int:
        """Ajusta el volumen en caliente entre 1 y 150."""
        self.volume = max(1, min(volume, 150))

        if (
            self.voice_client
            and self.voice_client.source
            and isinstance(self.voice_client.source, discord.PCMVolumeTransformer)
        ):
            self.voice_client.source.volume = self.volume / 100.0

        return self.volume

    def set_inactivity_timeout(self, seconds: int) -> None:
        """Modifica el tiempo de espera antes de desconectar por inactividad."""
        self._timeout_seconds = max(30, seconds)

    def _cancel_timeout(self) -> None:
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()

        self._timeout_task = None

    async def _inactivity_timeout(self) -> None:
        try:
            await asyncio.sleep(self._timeout_seconds)
            await self.disconnect()
        except asyncio.CancelledError:
            pass

    async def handle_empty_channel(self) -> None:
        if self._empty_channel_task and not self._empty_channel_task.done():
            return

        if self.is_playing:
            self.pause()

        self._empty_channel_task = asyncio.create_task(self._empty_channel_timeout())

    async def _empty_channel_timeout(self) -> None:
        try:
            await asyncio.sleep(self._empty_grace_seconds)
            await self.disconnect()
        except asyncio.CancelledError:
            pass

    def cancel_empty_channel_timeout(self) -> None:
        if self._empty_channel_task and not self._empty_channel_task.done():
            self._empty_channel_task.cancel()
            self._empty_channel_task = None

            if self.is_paused:
                self.resume()

    def _start_playback_watchdog(self) -> None:
        if self._playback_watchdog_task and not self._playback_watchdog_task.done():
            return

        self._playback_watchdog_task = asyncio.create_task(self._playback_watchdog())

    def _cancel_playback_watchdog(self) -> None:
        if self._playback_watchdog_task and not self._playback_watchdog_task.done():
            self._playback_watchdog_task.cancel()

        self._playback_watchdog_task = None

    async def disconnect(self) -> None:
        self._cancel_timeout()
        self._cancel_playback_watchdog()

        if self._empty_channel_task and not self._empty_channel_task.done():
            self._empty_channel_task.cancel()

        self._empty_channel_task = None

        self.queue.clear()
        self.current_track = None

        if self.listener and hasattr(self.listener, "disable_current_view"):
            await self.listener.disable_current_view()

        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            self.voice_client = None

    async def _playback_watchdog(self) -> None:
        try:
            while True:
                await asyncio.sleep(5)

                if self.voice_client is None:
                    return

                if self.current_track is None:
                    return

                if self._manual_stop:
                    return

                if self._play_previous:
                    return

                if not self.voice_client.is_connected():
                    continue

                if not self.voice_client.is_playing() and not self.voice_client.is_paused():
                    logger.warning(
                        "Watchdog: reproducción detenida. track=%s connected=%s playing=%s paused=%s",
                        self.current_track.title,
                        self.voice_client.is_connected(),
                        self.voice_client.is_playing(),
                        self.voice_client.is_paused(),
                    )

                    await self.play_next()
                    return

        except asyncio.CancelledError:
            pass

    async def play_next(self) -> None:
        """Adquiere el lock y procesa la siguiente cancion."""
        async with self._play_lock:
            await self._play_next()

    async def _play_next(self) -> None:
        self._cancel_timeout()

        if self.voice_client is None or not self.voice_client.is_connected():
            return

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            return

        while True:
            # 1. Seleccion de pista
            if self._next_track is not None:
                track = self._next_track
                self._next_track = None
                self._manual_stop = False

            elif self._manual_stop:
                self._manual_stop = False
                return

            elif self._play_previous:
                track = self.current_track
                self._play_previous = False

            elif self.current_track and self.current_track.loop:
                track = self.current_track

            else:
                if self.queue.is_empty() and self.autoplay and self.queue.has_previous():
                    last_track = self.queue.get_history()[-1]

                    logger.info(
                        "Cola vacia. Consultando recomendacion para '%s'...",
                        last_track.title,
                    )

                    recommended = await self.recommender.get_recommendation(
                        seed_track=last_track,
                        history=self.queue.get_history(),
                    )

                    if recommended:
                        self.queue.add_track(recommended)

                track = self.queue.get_next()

            if track is None:
                self.current_track = None

                if self.listener:
                    await self.listener.on_queue_empty()

                self._cancel_timeout()
                self._timeout_task = asyncio.create_task(self._inactivity_timeout())
                return

            self.current_track = track

            # 2. Extraccion del stream
            audio_data = await get_audio_stream(track.search_query)

            if audio_data and "url" in audio_data:
                track.audio_stream_url = audio_data["url"]

                raw_source = discord.FFmpegPCMAudio(
                    track.audio_stream_url,
                    **FFMPEG_OPTIONS,
                )

                source = discord.PCMVolumeTransformer(
                    raw_source,
                    volume=self.volume / 100.0,
                )

                self.voice_client.play(
                    source,
                    after=self._on_playback_end,
                )

                self._start_playback_watchdog()

                if self.listener:
                    await self.listener.on_track_start(track)

                return

            # Error iterativo: intenta con la siguiente pista
            logger.warning(
                "Fallo al resolver '%s'. Saltando a siguiente pista...",
                track.title,
            )

            if self.listener:
                await self.listener.on_track_error(
                    track,
                    RuntimeError("No se pudo resolver el stream de audio."),
                )

            self.current_track = None

    def _on_playback_end(self, error: Exception | None) -> None:
        """Puente sincronico hacia el event loop de asyncio."""
        asyncio.run_coroutine_threadsafe(
            self._handle_playback_completion(error),
            self.bot.loop,
        )

    async def _handle_playback_completion(self, error: Exception | None) -> None:
        """Gestiona el fin del stream y emite eventos de finalizacion."""
        finished_track = self.current_track

        if error:
            logger.error("[FFMPEG ERROR] Error durante la reproduccion: %s", error)
            if finished_track:
                if finished_track.loop:
                    finished_track.loop = False
                if self.listener:
                    await self.listener.on_track_error(finished_track, error)
        else:
            # Notifica que la pista concluyo con exito
            if finished_track and self.listener and hasattr(self.listener, "on_track_end"):
                await self.listener.on_track_end(finished_track)

        await self.play_next()

    def pause(self) -> bool:
        if self.is_playing:
            self.voice_client.pause()
            return True

        return False

    def resume(self) -> bool:
        if self.is_paused:
            self.voice_client.resume()
            return True

        return False

    def skip(self) -> bool:
        if self.voice_client is None:
            return False

        if self.is_playing or self.is_paused:
            self._manual_stop = False
            self.voice_client.stop()
            return True

        return False

    def stop(self) -> None:
        self._manual_stop = True
        self._play_previous = False
        self.queue.clear()
        self.current_track = None

        if self.voice_client is not None and (self.is_playing or self.is_paused):
            self.voice_client.stop()
            self._cancel_timeout()
            self._timeout_task = asyncio.create_task(self._inactivity_timeout())

    def previous(self) -> bool:
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
        if self.current_track is None:
            return False

        self.current_track.loop = not self.current_track.loop
        return self.current_track.loop

    async def play_now(self, position: int) -> bool:
        """Extrae una pista de la cola y la reproduce inmediatamente."""
        async with self._play_lock:
            if self.voice_client is None:
                return False

            total_tracks = len(self.queue)

            if position < 1 or position > total_tracks:
                return False

            index = position - 1
            track = self.queue.remove(index)

            if track is None:
                return False

            self._next_track = track
            self._manual_stop = True

            if self.voice_client.is_playing() or self.voice_client.is_paused():
                self.voice_client.stop()
            else:
                self._manual_stop = False
                await self._play_next()

            return True

    def move_current_to(self, position: int) -> bool:
        """Mueve la pista actual a una posicion sin duplicarla en el historial."""
        if self.current_track is None or self.voice_client is None:
            return False

        max_position = len(self.queue) + 1

        if position < 1 or position > max_position:
            return False

        track_to_move = self.current_track
        target_index = position - 1

        if not self.queue.move_current(
            track_to_move,
            target_index,
        ):
            return False

        track_to_move.loop = False
        self.current_track = None
        self._manual_stop = False

        self.voice_client.stop()
        return True
