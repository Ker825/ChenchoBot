import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.music.models import Track
from chencho_bot.services.spotify import (
    get_playlist_tracks,
    get_track_by_url,
    search_track,
)
from chencho_bot.utils.embeds import build_added_track_embed

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    """Comandos relacionados con reproducción musical."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def get_player(self, guild_id: int):
        """Obtiene el reproductor asociado al servidor."""
        return self.bot.get_player(guild_id)

    async def _get_voice_client(
        self,
        interaction: discord.Interaction,
    ) -> discord.VoiceClient | None:

        if interaction.guild is None:
            return None

        voice_client = interaction.guild.voice_client

        if voice_client is not None:
            return voice_client

        if not isinstance(interaction.user, discord.Member):
            return None

        if interaction.user.voice is None:
            return None

        channel = interaction.user.voice.channel

        try:
            return await channel.connect(
                timeout=10.0,
                reconnect=True,
            )

        except TimeoutError:
            await interaction.followup.send(
                "Se agotó el tiempo al conectar al canal de voz."
            )

        except discord.ClientException as error:
            await interaction.followup.send(f"Error al conectar: {error}")

        return None

    async def _resolve_query(
        self,
        query: str,
    ) -> list[dict]:

        loop = asyncio.get_running_loop()

        if "spotify.com" in query and "/track/" in query:
            result = await loop.run_in_executor(
                None,
                get_track_by_url,
                query,
            )

            return [result] if result else []

        if "spotify.com" in query and "/playlist/" in query:
            return await loop.run_in_executor(
                None,
                get_playlist_tracks,
                query,
            )

        result = await loop.run_in_executor(
            None,
            search_track,
            query,
        )

        return [result] if result else []

    @staticmethod
    def _create_track(
        track_info: dict,
        requester: discord.Member | None = None,
    ) -> Track:
        """Convierte los datos de Spotify en un Track."""

        search_query = f"{track_info['title']} {track_info['artist']} audio"

        return Track(
            title=track_info["title"],
            artist=track_info["artist"],
            album=track_info["album"],
            spotify_url=track_info["url"],
            search_query=search_query,
            cover_url=track_info.get("cover_url"),
            duration_ms=track_info.get("duration_ms", 0),
            requester=requester,
        )

    # ---------------------------------------------------------
    # PLAY
    # ---------------------------------------------------------

    @app_commands.command(
        name="play",
        description="Reproduce una canción de Spotify",
    )
    async def play(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "No se pudo identificar al usuario.",
                ephemeral=True,
            )
            return

        if interaction.user.voice is None:
            await interaction.followup.send(
                "No estás en un canal de voz.",
                ephemeral=True,
            )
            return

        voice_client = await self._get_voice_client(interaction)

        if voice_client is None:
            return

        results = await self._resolve_query(query)

        if not results:
            await interaction.followup.send("No se encontraron canciones.")
            return

        player = self.get_player(interaction.guild.id)

        player.voice_client = voice_client
        player.text_channel = interaction.channel

        tracks = [
            self._create_track(
                track_info,
                requester=interaction.user,
            )
            for track_info in results
        ]

        # Comprobamos el estado ANTES de añadir las canciones.
        was_idle = not player.is_playing and not player.is_paused

        # Añadir todas las canciones a la cola.
        for track in tracks:
            player.queue.add_track(track)

        logger.debug(
            "[bold cyan][DEBUG PLAY][/bold cyan] Canciones añadidas: [yellow]%s[/yellow]",
            len(tracks),
        )
        logger.debug(
            "[bold cyan][DEBUG PLAY][/bold cyan] Cola actual: [magenta]%s[/magenta]",
            len(player.queue),
        )
        logger.debug(
            "[bold cyan][DEBUG PLAY][/bold cyan] was_idle=[green]%s[/green]",
            was_idle,
        )

        # Si el reproductor estaba detenido,
        # comenzar la reproducción.
        if was_idle:
            logger.debug(
                "[bold yellow][DEBUG PLAY][/bold yellow] Iniciando [italic]play_next()[/italic]..."
            )
            await player.play_next()
        else:
            logger.debug(
                "[bold cyan][DEBUG PLAY][/bold cyan] El reproductor ya estaba activo."
            )

        # -----------------------------------------------------
        # Respuesta al usuario
        # -----------------------------------------------------

        if len(tracks) > 1:
            await interaction.followup.send(
                f"Se añadieron {len(tracks)} canciones a la cola."
            )
            return

        track = tracks[0]

        position = len(player.queue)

        embed = build_added_track_embed(
            track=track,
            position=position,
        )

        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # SKIP
    # ---------------------------------------------------------

    @app_commands.command(
        name="skip",
        description="Salta la canción actual",
    )
    async def skip(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if not player.skip():
            await interaction.followup.send("No hay ninguna canción reproduciéndose.")
            return

        await interaction.followup.send("Canción saltada.")

    # ---------------------------------------------------------
    # PAUSE
    # ---------------------------------------------------------

    @app_commands.command(
        name="pause",
        description="Pausa la canción actual",
    )
    async def pause(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if player.pause():
            await interaction.followup.send("Reproducción pausada.")
        else:
            await interaction.followup.send("No hay ninguna canción reproduciéndose.")

    # ---------------------------------------------------------
    # RESUME
    # ---------------------------------------------------------

    @app_commands.command(
        name="resume",
        description="Reanuda la canción pausada",
    )
    async def resume(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if player.resume():
            await interaction.followup.send("Reproducción reanudada.")
        else:
            await interaction.followup.send("No hay ninguna canción pausada.")

    # ---------------------------------------------------------
    # STOP
    # ---------------------------------------------------------

    @app_commands.command(
        name="stop",
        description="Detiene la reproducción y limpia la cola",
    )
    async def stop(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        player.stop()

        await interaction.followup.send("Reproducción detenida y cola limpiada.")

    # ---------------------------------------------------------
    # QUEUE
    # ---------------------------------------------------------

    @app_commands.command(
        name="queue",
        description="Muestra la cola de reproducción",
    )
    async def queue(
        self,
        interaction: discord.Interaction,
    ) -> None:

        if interaction.guild is None:
            await interaction.response.send_message(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        queue_list = player.queue.get_tracks()

        if not queue_list:
            await interaction.response.send_message(
                "La cola de reproducción está vacía."
            )
            return

        queue_message = "\n".join(
            f"{index}. **{track.title}** - {track.artist}"
            for index, track in enumerate(
                queue_list,
                start=1,
            )
        )

        await interaction.response.send_message(
            f"**Cola de reproducción:**\n{queue_message}"
        )

    # ---------------------------------------------------------
    # PREVIOUS
    # ---------------------------------------------------------

    @app_commands.command(
        name="previous",
        description="Reproduce la canción anterior",
    )
    async def previous(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        if player.previous():
            await interaction.followup.send("Reproduciendo canción anterior.")
        else:
            await interaction.followup.send("No hay ninguna canción anterior.")

    # ---------------------------------------------------------
    # LOOP
    # ---------------------------------------------------------

    @app_commands.command(
        name="loop",
        description="Alterna el modo de repetición",
    )
    async def loop(
        self,
        interaction: discord.Interaction,
    ) -> None:

        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send(
                "Comando solo disponible en servidores.",
                ephemeral=True,
            )
            return

        player = self.get_player(interaction.guild.id)

        # loop() devuelve True o False.
        loop_enabled = player.loop()

        status = "activado" if loop_enabled else "desactivado"

        await interaction.followup.send(f"Modo de repetición {status}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
