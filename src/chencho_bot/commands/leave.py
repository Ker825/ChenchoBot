import discord
from discord import app_commands
from discord.ext import commands


class Leave(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leave", description="Sal del canal de voz")
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if interaction.guild.voice_client is None:
            await interaction.followup.send("No estoy en un canal de voz.")
            return

        await interaction.guild.voice_client.disconnect()
        await interaction.followup.send("Me he desconectado del canal de voz.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leave(bot))
