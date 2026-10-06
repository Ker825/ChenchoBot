import logging

import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.services.resolver import TrackResolver
from chencho_bot.utils.guards import VoiceGuard
from chencho_bot.utils.ui.embeds import build_status_embed
from chencho_bot.utils.ui.search_view import SearchSelectView

logger = logging.getLogger(__name__)


class Search(commands.Cog):
    """Controlador de busqueda interactiva de canciones."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.resolver = TrackResolver()

    @app_commands.command(
        name="search",
        description="Busca canciones y permite seleccionar cual anadir a la cola.",
    )
    @app_commands.describe(query="Termino de busqueda o enlace de Spotify")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()

        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        assert isinstance(interaction.user, discord.Member)

        tracks = await self.resolver.resolve(query, requester=interaction.user)

        if not tracks:
            embed = build_status_embed(
                f"No se encontraron resultados para: **{query}**",
                success=False,
            )
            await interaction.followup.send(embed=embed)
            return

        # Si se paso un enlace directo que devuelve una sola pista
        if len(tracks) == 1:
            music_cog = self.bot.get_cog("Music")
            if not music_cog or not hasattr(music_cog, "get_player"):
                embed = build_status_embed(
                    "El servicio de musica no esta disponible.",
                    success=False,
                )
                await interaction.followup.send(embed=embed)
                return

            player = music_cog.get_player(
                interaction.guild.id,
                channel=interaction.channel,
            )
            player.queue.add_track(tracks[0])

            embed = build_status_embed(
                f"Anadida a la cola: **{tracks[0].title}** de **{tracks[0].artist}**.",
                success=True,
            )
            await interaction.followup.send(embed=embed)

            if not player.is_playing:
                await player.play_next()
            return

        # Presentacion con la vista desacoplada
        view = SearchSelectView(
            tracks=tracks,
            bot=self.bot,
            guild_id=interaction.guild.id,
            requester=interaction.user,
        )

        embed = discord.Embed(
            title="Resultados de busqueda",
            description=f"Resultados para: **{query}**\nSelecciona una cancion en el menu inferior.",
            color=0x1DB954,
        )
        for idx, track in enumerate(tracks[:5], start=1):
            embed.add_field(
                name=f"{idx}. {track.title}",
                value=f"{track.artist} | {track.album}",
                inline=False,
            )

        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Search(bot))
