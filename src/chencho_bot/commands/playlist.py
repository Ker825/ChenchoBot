import logging

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.exc import IntegrityError

from chencho_bot.database.repositories.playlist_repository import PlaylistRepository
from chencho_bot.database.session import async_session_factory
from chencho_bot.music.models import Track
from chencho_bot.services.resolver import TrackResolver
from chencho_bot.utils.ui.embeds import build_lists_embed, build_status_embed

logger = logging.getLogger(__name__)


class PlaylistCommands(commands.Cog):
    """Comandos slash para la administracion y reproduccion de listas personalizadas."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.resolver = TrackResolver()

    playlist_group = app_commands.Group(
        name="playlist",
        description="Gestion y reproduccion de listas de musica personalizadas.",
    )

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        """Garantiza la conexion activa del bot al canal de voz del usuario."""
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
            await interaction.followup.send(f"Error al conectar al canal de voz: {error}", ephemeral=True)
            return None

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    @playlist_group.command(name="create", description="Crea una nueva lista de reproduccion personal.")
    @app_commands.describe(name="Nombre unico para tu lista (maximo 64 caracteres)")
    async def create(self, interaction: discord.Interaction, name: str) -> None:
        """Crea"""
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        clean_name = name.strip()
        if len(clean_name) > 64:
            await interaction.followup.send(
                "El nombre de la lista no puede exceder 64 caracteres.",
                ephemeral=True,
            )
            return

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            try:
                await repo.create_playlist(
                    guild_id=interaction.guild.id,
                    creator_id=interaction.user.id,
                    name=clean_name,
                )
                await session.commit()
                embed = build_status_embed(
                    message=f"Lista **{clean_name}** creada correctamente.",
                    success=True,
                )
            except IntegrityError:
                await session.rollback()
                embed = build_status_embed(
                    message=f"Ya tienes una lista llamada **{clean_name}** en este servidor.",
                    success=False,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------------------------------------------------------
    # ADD
    # ---------------------------------------------------------

    @playlist_group.command(name="add", description="Agrega una cancion a tu lista de reproduccion.")
    @app_commands.describe(
        name="Nombre de tu lista",
        query="Titulo, enlace de Spotify o busqueda",
    )
    async def add(self, interaction: discord.Interaction, name: str, query: str) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        clean_name = name.strip()

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            playlist = await repo.get_playlist(
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                name=clean_name,
            )
            if not playlist:
                embed = build_status_embed(
                    message=f"No se encontro ninguna lista tuya con el nombre **{clean_name}**.",
                    success=False,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            resolved_tracks = await self.resolver.resolve(
                query=query,
                requester=interaction.user,  # type: ignore
            )
            if not resolved_tracks:
                embed = build_status_embed(
                    message="No se encontraron pistas que coincidan con la busqueda.",
                    success=False,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            added_count = 0
            for track in resolved_tracks:
                await repo.add_track(playlist_id=playlist.id, track=track)
                added_count += 1

            await session.commit()

        status_msg = (
            f"Se anadieron {added_count} canciones a **{clean_name}**."
            if added_count > 1
            else f"Se anadio **{resolved_tracks[0].title}** a **{clean_name}**."
        )
        embed = build_status_embed(message=status_msg, success=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------------------------------------------------------
    # PLAY
    # ---------------------------------------------------------

    @playlist_group.command(name="play", description="Carga y reproduce una de tus listas guardadas.")
    @app_commands.describe(name="Nombre de la lista que deseas reproducir")
    async def play(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()

        voice_client = await self._ensure_voice(interaction)
        if not voice_client or not interaction.guild or not interaction.channel:
            return

        clean_name = name.strip()

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            playlist = await repo.get_playlist(
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                name=clean_name,
            )

        if not playlist or not playlist.tracks:
            embed = build_status_embed(
                message=f"La lista **{clean_name}** no existe o no contiene canciones.",
                success=False,
            )
            await interaction.followup.send(embed=embed)
            return

        music_cog = self.bot.get_cog("Music")
        if not music_cog or not hasattr(music_cog, "get_player"):
            embed = build_status_embed(
                message="El servicio de reproduccion musical no esta disponible.",
                success=False,
            )
            await interaction.followup.send(embed=embed)
            return

        player = music_cog.get_player(interaction.guild.id, channel=interaction.channel)
        player.voice_client = voice_client

        if hasattr(music_cog, "_ensure_ui_handler"):
            music_cog._ensure_ui_handler(
                guild_id=interaction.guild.id,
                channel=interaction.channel,
                player=player,
            )

        was_idle = not player.is_playing and not player.is_paused

        domain_tracks = [
            Track(
                title=item.title,
                artist=item.artist,
                album="Lista Personalizada",
                spotify_url=item.spotify_url or "",
                search_query=item.search_query,
                duration_ms=item.duration_ms,
                requester=interaction.user,  # type: ignore
            )
            for item in playlist.tracks
        ]

        player.queue.add_tracks(domain_tracks)

        if was_idle:
            await player.play_next()

        embed = build_status_embed(
            message=f"Cargadas {len(domain_tracks)} canciones desde la lista **{clean_name}**.",
            success=True,
        )
        await interaction.followup.send(embed=embed)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    @playlist_group.command(name="list", description="Muestra todas tus listas creadas en este servidor.")
    async def list_playlists(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            playlists = await repo.list_user_playlists(
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
            )

        if not playlists:
            embed = build_status_embed(
                message="No tienes listas de reproduccion creadas en este servidor.",
                success=False,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = [f"`{idx}.` **{pl.name}**" for idx, pl in enumerate(playlists, start=1)]

        embed = build_lists_embed(
            guild_name=interaction.guild.name,
            lines=lines,
            total_lists=len(playlists),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------------------------------------------------------
    # REMOVE TRACK
    # ---------------------------------------------------------

    @playlist_group.command(name="remove_track", description="Elimina una pista de tu lista segun su posicion.")
    @app_commands.describe(
        name="Nombre de tu lista",
        position="Numero de posicion de la pista a remover",
    )
    async def remove_track(
        self,
        interaction: discord.Interaction,
        name: str,
        position: app_commands.Range[int, 1],
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        clean_name = name.strip()

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            playlist = await repo.get_playlist(
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                name=clean_name,
            )
            if not playlist:
                embed = build_status_embed(
                    message=f"No se encontro la lista **{clean_name}**.",
                    success=False,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            removed = await repo.remove_track(playlist_id=playlist.id, position=position)
            if removed:
                await session.commit()
                embed = build_status_embed(
                    message=f"Pista en posicion {position} eliminada de **{clean_name}**.",
                    success=True,
                )
            else:
                embed = build_status_embed(
                    message=f"No existe ninguna pista en la posicion {position} de **{clean_name}**.",
                    success=False,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    @playlist_group.command(name="delete", description="Elimina definitivamente una lista de reproduccion.")
    @app_commands.describe(name="Nombre de la lista a eliminar")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        clean_name = name.strip()

        async with async_session_factory() as session:
            repo = PlaylistRepository(session)
            deleted = await repo.delete_playlist(
                guild_id=interaction.guild.id,
                creator_id=interaction.user.id,
                name=clean_name,
            )
            if deleted:
                await session.commit()
                embed = build_status_embed(
                    message=f"Lista **{clean_name}** eliminada correctamente.",
                    success=True,
                )
            else:
                embed = build_status_embed(
                    message=f"No se encontro ninguna lista con el nombre **{clean_name}**.",
                    success=False,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlaylistCommands(bot))
