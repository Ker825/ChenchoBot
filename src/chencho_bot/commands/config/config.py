import logging

import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.database.models import GuildConfig
from chencho_bot.services.guild_config import GuildConfigService
from chencho_bot.utils.ui.embeds import COLOR_PRIMARY, build_status_embed

logger = logging.getLogger(__name__)


class AdminConfig(commands.Cog):
    """Controlador de configuracion administrativa y politicas por servidor."""

    def __init__(
        self,
        bot: commands.Bot,
        config_service: GuildConfigService | None = None,
    ) -> None:
        self.bot = bot
        self.config_service = config_service or GuildConfigService()

    config_group = app_commands.Group(
        name="config",
        description="Administracion y ajustes del reproductor en el servidor.",
        default_permissions=discord.Permissions(administrator=True),
    )

    @config_group.command(
        name="set_dj",
        description="Asigna o retira el rol obligatorio para controlar el reproductor.",
    )
    @app_commands.describe(role="Rol que tendra privilegios de DJ (dejar vacio para modo libre)")
    async def set_dj(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        role_id = role.id if role else None
        updated = await self.config_service.set_dj_role(interaction.guild.id, role_id)

        if updated:
            status_msg = (
                f"Rol de DJ asignado a: {role.mention}."
                if role
                else "Rol de DJ removido. El reproductor operara en modo libre."
            )
            embed = build_status_embed(message=status_msg, success=True)
        else:
            embed = build_status_embed(message="Fallo al actualizar la configuracion.", success=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_group.command(
        name="show",
        description="Visualiza la configuracion actual del servidor.",
    )
    async def show_config(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        config: GuildConfig = await self.config_service.get_config(interaction.guild.id)

        dj_info = f"<@&{config.dj_role_id}>" if config.dj_role_id else "No asignado (Modo libre)"
        channel_info = f"<#{config.music_channel_id}>" if config.music_channel_id else "Cualquiera"
        autoplay_info = "Activado" if config.autoplay_enabled else "Desactivado"

        embed = discord.Embed(
            title=f"Configuracion del Servidor - {interaction.guild.name}",
            color=COLOR_PRIMARY,
        )
        embed.add_field(name="Rol DJ", value=dj_info, inline=True)
        embed.add_field(name="Canal de Musica Dedicado", value=channel_info, inline=True)
        embed.add_field(name="Volumen Base", value=f"{config.default_volume}%", inline=True)
        embed.add_field(name="Autoplay Predeterminado", value=autoplay_info, inline=True)
        embed.add_field(
            name="Tiempo de Inactividad",
            value=f"{config.inactivity_timeout_seconds} segundos",
            inline=True,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_group.command(
        name="timeout",
        description="Ajusta el tiempo de espera antes de desconectar por inactividad.",
    )
    @config_group.command(
        name="volume",
        description="Establece el volumen base predeterminado para el servidor.",
    )
    @app_commands.describe(percent="Volumen base predeterminado (1 - 150)")
    async def set_default_volume(
        self,
        interaction: discord.Interaction,
        percent: app_commands.Range[int, 1, 150],
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        updated = await self.config_service.update_config(
            guild_id=interaction.guild.id,
            default_volume=percent,
        )

        # Propagacion reactiva al reproductor en memoria si esta activo
        music_cog = self.bot.get_cog("Music")
        if music_cog and hasattr(music_cog, "players") and interaction.guild.id in music_cog.players:
            music_cog.players[interaction.guild.id].set_volume(percent)

        if updated:
            embed = build_status_embed(
                message=f"Volumen base establecido al **{percent}%**.",
                success=True,
            )
        else:
            embed = build_status_embed(message="Error al actualizar el volumen base.", success=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_group.command(
        name="autoplay",
        description="Activa o desactiva el modo Autoplay predeterminado en el servidor.",
    )
    @app_commands.describe(enabled="Verdadero para mantener autoplay activo por defecto")
    async def set_default_autoplay(
        self,
        interaction: discord.Interaction,
        enabled: bool,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        updated = await self.config_service.update_config(
            guild_id=interaction.guild.id,
            autoplay_enabled=enabled,
        )

        # Propagacion reactiva al reproductor en memoria
        music_cog = self.bot.get_cog("Music")
        if music_cog and hasattr(music_cog, "players") and interaction.guild.id in music_cog.players:
            music_cog.players[interaction.guild.id].autoplay = enabled

        status = "activado" if enabled else "desactivado"
        if updated:
            embed = build_status_embed(
                message=f"Autoplay predeterminado **{status}**.",
                success=enabled,
            )
        else:
            embed = build_status_embed(message="Error al configurar autoplay predeterminado.", success=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_group.command(
        name="timeout",
        description="Ajusta el tiempo de espera antes de desconectar por inactividad.",
    )
    @app_commands.describe(seconds="Tiempo de inactividad en segundos (30 - 600)")
    async def set_timeout(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 30, 600],
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            await interaction.followup.send("Comando solo disponible en servidores.", ephemeral=True)
            return

        updated = await self.config_service.update_config(
            guild_id=interaction.guild.id,
            inactivity_timeout_seconds=seconds,
        )

        # Propagacion reactiva al temporizador en memoria
        music_cog = self.bot.get_cog("Music")
        if music_cog and hasattr(music_cog, "players") and interaction.guild.id in music_cog.players:
            music_cog.players[interaction.guild.id].set_inactivity_timeout(seconds)

        if updated:
            embed = build_status_embed(
                message=f"Tiempo de inactividad establecido a **{seconds}** segundos.",
                success=True,
            )
        else:
            embed = build_status_embed(message="Error al actualizar el tiempo de espera.", success=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminConfig(bot))
