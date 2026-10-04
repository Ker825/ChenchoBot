import logging

import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.music.player import MusicPlayer
from chencho_bot.services.resolver import TrackResolver
from chencho_bot.utils.guards import VoiceGuard
from chencho_bot.utils.ui.discord_handler import DiscordUIHandler
from chencho_bot.utils.ui.embeds import build_added_track_embed, build_queue_page_embed, build_status_embed
from chencho_bot.utils.ui.queue_view import QueuePaginationView

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    """Controlador de comandos slash para el servicio de musica."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.resolver = TrackResolver()
        self.ui_handlers: dict[int, DiscordUIHandler] = {}
        self.players: dict[int, MusicPlayer] = {}

    def get_player(
        self,
        guild_id: int,
        channel: discord.abc.Messageable | None = None,
    ) -> MusicPlayer:
        """Obtiene o instancia el MusicPlayer vinculandolo a su DiscordUIHandler."""
        if guild_id not in self.players:
            player = MusicPlayer(self.bot)

            # Si se proporciona el canal de texto, se enlaza el adaptador de UI
            if channel:
                ui_handler = DiscordUIHandler(text_channel=channel, player=player)
                player.listener = ui_handler
                self.ui_handlers[guild_id] = ui_handler

            self.players[guild_id] = player

        return self.players[guild_id]

    def remove_player(self, guild_id: int) -> None:
        """Remueve las instancias de dominio y presentacion para liberar memoria."""
        self.players.pop(guild_id, None)
        self.ui_handlers.pop(guild_id, None)

    def _ensure_ui_handler(
        self,
        guild_id: int,
        channel: discord.abc.Messageable,
        player: MusicPlayer,
    ) -> DiscordUIHandler:
        """Garantiza la existencia y canal actualizado del adaptador de UI."""
        if guild_id not in self.ui_handlers:
            handler = DiscordUIHandler(text_channel=channel, player=player)
            self.ui_handlers[guild_id] = handler
            player.listener = handler
        else:
            handler = self.ui_handlers[guild_id]
            handler.text_channel = channel

        return handler

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return None

        if interaction.guild.voice_client:
            return interaction.guild.voice_client

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Debes unirte a un canal de voz.", ephemeral=True)
            return None

        try:
            return await interaction.user.voice.channel.connect(timeout=10.0, reconnect=True)
        except (TimeoutError, discord.ClientException) as error:
            await interaction.followup.send(f"Error al conectar: {error}", ephemeral=True)
            return None

    # ---------------------------------------------------------
    # PLAY
    # ---------------------------------------------------------

    @app_commands.command(name="play", description="Reproduce una cancion de Spotify")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()

        voice_client = await self._ensure_voice(interaction)
        if not voice_client or not interaction.guild or not interaction.channel:
            return

        tracks = await self.resolver.resolve(
            query,
            requester=interaction.user,  # type: ignore
        )
        if not tracks:
            await interaction.followup.send("No se encontraron canciones.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)
        player.voice_client = voice_client

        # Conectar el adaptador de interfaz con el canal actual
        self._ensure_ui_handler(
            guild_id=interaction.guild.id,
            channel=interaction.channel,
            player=player,
        )

        was_idle = not player.is_playing and not player.is_paused

        for track in tracks:
            player.queue.add_track(track)

        if was_idle:
            await player.play_next()

        if len(tracks) > 1:
            await interaction.followup.send(f"Se anadieron {len(tracks)} canciones a la cola.")
        else:
            embed = build_added_track_embed(track=tracks[0], position=len(player.queue))
            await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # AUTO PLAY
    # ---------------------------------------------------------

    @app_commands.command(
        name="autoplay",
        description="Alterna el modo de reproduccion continua automatica.",
    )
    async def autoplay(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)
        player.autoplay = not player.autoplay

        status = "activado" if player.autoplay else "desactivado"
        embed = build_status_embed(
            message=f"Modo Autoplay **{status}**.",
            success=player.autoplay,
        )
        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # SKIP
    # ---------------------------------------------------------

    @app_commands.command(
        name="skip",
        description="Salta la canción actual",
    )
    async def skip(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if player.skip():
            embed = build_status_embed("Cancion saltada.", success=True)
        else:
            embed = build_status_embed("No hay ninguna cancion en reproduccion.", success=False)

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # PAUSE
    # ---------------------------------------------------------

    @app_commands.command(name="pause", description="Pausa la cancion actual")
    async def pause(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)

        if player.pause():
            embed = build_status_embed("Reproduccion pausada.", success=True)
        else:
            embed = build_status_embed("No hay ninguna cancion en reproduccion.", success=False)

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # RESUME
    # ---------------------------------------------------------

    @app_commands.command(name="resume", description="Reanuda la cancion pausada")
    async def resume(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)

        if player.resume():
            embed = build_status_embed("Reproduccion reanudada.", success=True)
        else:
            embed = build_status_embed("No hay ninguna cancion pausada.", success=False)

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # STOP
    # ---------------------------------------------------------

    @app_commands.command(
        name="stop",
        description="Detiene la musica y limpia la cola sin salir del canal.",
    )
    async def stop(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        # 1. Validar presencia en canal de voz
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        guild_id = interaction.guild.id

        if interaction.guild.voice_client is None:
            embed = build_status_embed(
                "No hay ninguna sesion activa de reproduccion.",
                success=False,
            )
            await interaction.followup.send(embed=embed)
            return

        player = self.get_player(guild_id)

        # 2. Detener reproduccion y programar temporizador de inactividad
        player.stop()

        # 3. Desactivar botonera activa si existe un handler registrado
        if guild_id in self.ui_handlers:
            await self.ui_handlers[guild_id].disable_current_view()

        embed = build_status_embed(
            "Reproduccion detenida y cola vaciada. Entrando en modo de espera.",
            success=True,
        )
        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # GRUPO DE COMANDOS: /queue
    # ---------------------------------------------------------

    queue_group = app_commands.Group(
        name="queue",
        description="Comandos para la administracion de la cola musical.",
    )

    @queue_group.command(name="show", description="Visualiza las canciones en espera.")
    async def queue_show(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)
        queue_tracks = player.queue.get_tracks()

        if not queue_tracks:
            await interaction.response.send_message(
                "La cola de reproduccion esta vacia.",
                ephemeral=True,
            )
            return

        embed = build_queue_page_embed(queue_tracks, current_page=1, per_page=10)
        view = QueuePaginationView(tracks=queue_tracks, per_page=10)

        # Si solo hay una pagina, enviamos solo el embed sin botones innecesarios
        if view.total_pages <= 1:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    @queue_group.command(
        name="shuffle",
        description="Mezcla aleatoriamente las canciones en espera.",
    )
    async def queue_shuffle(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)

        if player.queue.shuffle():
            embed = build_status_embed(
                message="Cola de reproduccion mezclada.",
                success=True,
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = build_status_embed(
                message="No hay suficientes canciones para mezclar la cola.",
                success=False,
            )
            await interaction.followup.send(
                embed=embed,
                ephemeral=False,
            )

    @queue_group.command(
        name="remove",
        description="Elimina una cancion de la cola segun su numero de posicion.",
    )
    @app_commands.describe(position="Numero de la cancion en la lista (visible en /queue show)")
    async def queue_remove(
        self,
        interaction: discord.Interaction,
        position: app_commands.Range[int, 1],
    ) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)

        # Conversion: la UI muestra base 1, pero la coleccion opera base 0
        removed_track = player.queue.remove(index=position - 1)

        if removed_track:
            embed = build_status_embed(
                message=f"Eliminada de la cola: **{removed_track.title}** - {removed_track.artist}",
                success=True,
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = build_status_embed(
                f"Posicion {position} invalida. Consulta las posiciones con `/queue show`.",
                success=False,
            )
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

    @queue_group.command(
        name="move",
        description="Mueve la cancion actual a una posicion especifica de la cola.",
    )
    @app_commands.describe(to_position="Posicion en la cola donde deseas reubicar la cancion actual")
    async def queue_move(
        self,
        interaction: discord.Interaction,
        to_position: app_commands.Range[int, 1],
    ) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)

        if not player.current_track:
            await interaction.followup.send(
                "No hay ninguna cancion reproduciendose actualmente.",
                ephemeral=True,
            )
            return

        track_title = player.current_track.title

        if player.move_current_to(to_position):
            await interaction.followup.send(
                f"La cancion **{track_title}** se movio a la posicion {to_position} de la cola."
            )
        else:
            max_pos = len(player.queue) + 1
            await interaction.followup.send(
                f"Posicion invalida. Indica una posicion entre 1 y {max_pos}.",
                ephemeral=True,
            )

    @queue_group.command(
        name="play_now",
        description="Reproduce inmediatamente una canción de la cola",
    )
    async def queue_play_now(
        self,
        interaction: discord.Interaction,
        position: int,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if not await player.play_now(position):
            await interaction.followup.send(
                "La posición indicada no es válida.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Reproduciendo ahora la canción en la posición **{position}**.",
            ephemeral=True,
        )

    @queue_group.command(
        name="clear",
        description="Vacia todas las canciones en espera (sin afectar la actual).",
    )
    async def queue_clear(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)

        if player.queue.is_empty():
            embed = build_status_embed(
                message="La cola ya se encuentra vacia.",
                success=False,
            )
            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )
            return

        player.queue.clear()
        embed = build_status_embed(
            message="Se han eliminado todas las pistas en espera.",
            success=True,
        )
        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # PREVIOUS
    # ---------------------------------------------------------

    @app_commands.command(name="previous", description="Reproduce la cancion anterior")
    async def previous(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)

        if player.previous():
            await interaction.followup.send("Reproduciendo cancion anterior.")
        else:
            await interaction.followup.send("No hay ninguna cancion anterior.")

    # ---------------------------------------------------------
    # LOOP
    # ---------------------------------------------------------

    @app_commands.command(name="loop", description="Alterna la repeticion de la pista actual.")
    async def loop(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        player = self.get_player(interaction.guild.id)

        if not player.current_track:
            embed = build_status_embed("No hay ninguna cancion en reproduccion.", success=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        loop_enabled = player.loop()
        status = "activado" if loop_enabled else "desactivado"
        embed = build_status_embed(f"Modo de repeticion **{status}**.", success=loop_enabled)

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # LISTENERS
    # ---------------------------------------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Supervisa el canal de voz para pausar o desconectar si los usuarios se van."""
        # Ignorar cambios provocados por bots
        if member.bot:
            return

        guild = member.guild
        voice_client: discord.VoiceClient | None = guild.voice_client

        if not voice_client or not voice_client.channel:
            return

        bot_channel = voice_client.channel
        player = self.get_player(guild.id)

        # 1. Caso: Un usuario salio del canal donde esta el bot
        if before.channel == bot_channel and after.channel != bot_channel:
            # Miembros humanos restantes en el canal
            human_members = [m for m in bot_channel.members if not m.bot]
            if len(human_members) == 0:
                logger.info(
                    "Canal de voz %s vacio en %s. Iniciando gracia de %ds...",
                    bot_channel.name,
                    guild.name,
                    player._empty_grace_seconds,
                )
                await player.handle_empty_channel()

        # 2. Caso: Un usuario se unio al canal donde esta el bot
        elif after.channel == bot_channel and before.channel != bot_channel:
            # Si habia una cuenta regresiva para desconectar, cancelarla
            if player._empty_channel_task and not player._empty_channel_task.done():
                logger.info(
                    "Usuario %s ingreso a %s. Cancelando desconexion por canal vacio.",
                    member.display_name,
                    bot_channel.name,
                )
                player.cancel_empty_channel_timeout()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
