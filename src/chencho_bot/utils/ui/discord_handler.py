import discord

from chencho_bot.music.events import PlayerEventListener
from chencho_bot.music.models import Track
from chencho_bot.music.player import MusicPlayer
from chencho_bot.utils.ui.embeds import build_now_playing_embed
from chencho_bot.utils.ui.view import PlayerControlsView


class DiscordUIHandler(PlayerEventListener):
    """Adaptador de salida: traduce eventos del dominio en vistas y mensajes de Discord."""

    def __init__(self, text_channel: discord.abc.Messageable, player: MusicPlayer) -> None:
        self.text_channel = text_channel
        self.player = player
        self.current_message: discord.Message | None = None
        self.current_view: PlayerControlsView | None = None

    async def disable_current_view(self) -> None:
        """Desactiva la botonera del mensaje activo para evitar botones huerfanos."""
        if self.current_message and self.current_view:
            try:
                self.current_view.disable_all()
                await self.current_message.edit(view=self.current_view)
            except discord.HTTPException:
                pass
            self.current_message = None
            self.current_view = None

    async def on_track_start(self, track: Track) -> None:
        """Se dispara al iniciar una nueva cancion: retira la tarjeta vieja y emite la nueva."""
        await self.disable_current_view()

        embed = build_now_playing_embed(track=track, current_ms=0)
        view = PlayerControlsView(player=self.player)

        self.current_view = view
        self.current_message = await self.text_channel.send(embed=embed, view=view)

    async def on_track_error(self, track: Track, error: Exception) -> None:
        """Informa fallos en el stream sin bloquear la interfaz."""
        await self.text_channel.send(f"Error al reproducir **{track.title}**. Omitiendo pista...")

    async def on_queue_empty(self) -> None:
        """Desactiva controles y avisa sobre la inactividad inminente."""
        await self.disable_current_view()
        await self.text_channel.send("La cola ha finalizado. El bot se desconectara si no hay actividad.")
