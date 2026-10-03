import discord
from discord import app_commands
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Comprueba la latencia del bot")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
