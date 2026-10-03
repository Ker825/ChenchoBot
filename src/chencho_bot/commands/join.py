import discord
from discord import app_commands
from discord.ext import commands


class Join(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="join", description="Unete a un canal de voz")
    async def join(self, interaction: discord.Interaction) -> None:
        # 1. Responder de inmediato para congelar la interacción
        await interaction.response.defer()

        # 2. Validar que la interacción ocurra en un servidor
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.followup.send(
                "Este comando solo puede usarse en un servidor.", ephemeral=True
            )
            return

        # 3. Validar estado de voz del usuario
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            await interaction.followup.send(
                "No estas en un canal de voz.", ephemeral=True
            )
            return

        # 4. Validar si el bot ya está conectado
        if interaction.guild.voice_client is not None:
            await interaction.followup.send(
                "Ya estoy en un canal de voz.", ephemeral=True
            )
            return

        channel = interaction.user.voice.channel

        # 5. Conexión con manejo de timeouts o errores de red
        try:
            await channel.connect(timeout=10.0, reconnect=True)
            await interaction.followup.send(f"Me he unido a {channel.name}.")
        except TimeoutError:
            await interaction.followup.send(
                "Se agoto el tiempo de espera al conectar al canal de voz."
            )
        except discord.ClientException as e:
            await interaction.followup.send(f"Error de cliente de voz: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Join(bot))
