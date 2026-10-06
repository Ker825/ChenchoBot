import asyncio
import logging

import discord
from discord.ext import commands

from chencho_bot.services.guild_config import GuildConfigService

logger = logging.getLogger(__name__)


class GuildLifecycleEvents(commands.Cog):
    """Sincroniza el estado de los servidores de Discord con PostgreSQL."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config_service = GuildConfigService()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Puebla la base de datos con todos los servidores donde el bot ya es miembro."""
        logger.info("Sincronizando configuraciones de servidores con PostgreSQL...")
        tasks = [self.config_service.get_config(guild.id) for guild in self.bot.guilds]
        if tasks:
            await asyncio.gather(*tasks)
            logger.info("Se sincronizaron %d servidores en guild_configs.", len(tasks))

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Registra la configuracion inicial al ingresar a un nuevo servidor."""
        logger.info("Bot anadido al servidor: %s (%d). Creando registro...", guild.name, guild.id)
        await self.config_service.get_config(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Limpia la cache en memoria si el bot es expulsado."""
        self.config_service.invalidate(guild.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GuildLifecycleEvents(bot))
