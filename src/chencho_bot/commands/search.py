import discord
from discord import app_commands
from discord.ext import commands


class Search(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="search", description="Busca una canción en Spotify")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        from chencho_bot.services.spotify import search_track

        result = search_track(query)
        if result is None:
            await interaction.response.send_message("No se encontró la canción.")
        else:
            await interaction.response.send_message(
                f"**{result['title']}** by **{result['artist']}**\n"
                f"Album: {result['album']}\n"
                f"[Escuchar en Spotify]({result['url']})"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))
