import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.commands.music import Music
from chencho_bot.services.spotify import get_track_by_url, search_track
from chencho_bot.utils.ui.embeds import build_searched_track_embed


class Search(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="search",
        description="Busca una canción en Spotify",
    )
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:

        loop = asyncio.get_running_loop()

        # URL directa de Spotify
        if "spotify.com" in query and "/track/" in query:
            result = await loop.run_in_executor(
                None,
                get_track_by_url,
                query,
            )

            loop = asyncio.get_running_loop()

            # URL directa de Spotify
            if "spotify.com" in query and "/track/" in query:
                result = await loop.run_in_executor(
                    None,
                    get_track_by_url,
                    query,
                )

                if result is None:
                    await interaction.response.send_message("No se pudo obtener la canción de Spotify.")
                    return

                track = Music._create_track(
                    result,
                    requester=interaction.user,
                )

                embed = build_searched_track_embed(
                    track=track,
                )

                await interaction.response.send_message(
                    embed=embed,
                )
                return

            # Búsqueda normal
        result = await loop.run_in_executor(
            None,
            search_track,
            query,
        )

        if result is None:
            await interaction.response.send_message("No se encontró la canción.")
            return

        await interaction.response.send_message(
            f"**{result['title']}** by **{result['artist']}**\n"
            f"Album: {result['album']}\n"
            f"[Escuchar en Spotify]({result['url']})"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))
