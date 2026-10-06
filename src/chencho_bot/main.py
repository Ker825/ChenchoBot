import logging
import os
import sys

import discord
from discord.ext import commands
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from chencho_bot.config.settings import ConfigurationError, get_settings
from chencho_bot.utils.logger import setup_logging

logger = logging.getLogger(__name__)
console = Console()

# Extensiones activas: se retira 'leave' al estar integrado en 'music'
EXTENSIONS_TO_LOAD: tuple[str, ...] = (
    "chencho_bot.commands.ping",
    "chencho_bot.commands.music",
    "chencho_bot.commands.search",
    "chencho_bot.commands.join",
    "chencho_bot.commands.leave",
    "chencho_bot.commands.playlist",
)


class ChenchoBot(commands.Bot):
    """Cliente central de Discord con inicialización controlada."""

    def __init__(self, test_guild_id: int | None = None) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )
        self.test_guild_id: int | None = test_guild_id

    async def setup_hook(self) -> None:
        """Carga las extensiones modulares y sincroniza el árbol de comandos."""
        table = Table(
            title="Carga de Extensiones",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Modulo", style="dim")
        table.add_column("Estado", justify="center")
        table.add_column("Detalle")

        for extension in EXTENSIONS_TO_LOAD:
            try:
                await self.load_extension(extension)
                table.add_row(
                    extension,
                    "[bold green]OK[/bold green]",
                    "Cargada correctamente",
                )
            except Exception as error:
                logger.exception("Error al cargar la extensión: %s", extension)
                table.add_row(
                    extension,
                    "[bold red]FAIL[/bold red]",
                    str(error),
                )

        console.print(table)

        # Sincronización restringida al servidor de pruebas si está definido
        if self.test_guild_id:
            guild_obj = discord.Object(id=self.test_guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            console.print(
                f"[bold blue]Tree Sync:[/bold blue] Sincronizados "
                f"[bold yellow]{len(synced)}[/bold yellow] comandos en el servidor de pruebas."
            )
        else:
            synced = await self.tree.sync()
            console.print(
                f"[bold blue]Tree Sync Global:[/bold blue] Sincronizados "
                f"[bold yellow]{len(synced)}[/bold yellow] comandos globalmente."
            )


def build_bot(test_guild_id: int | None) -> ChenchoBot:
    """Fábrica para instanciar el bot y registrar listeners de ciclo de vida del servidor."""
    bot = ChenchoBot(test_guild_id=test_guild_id)

    @bot.event
    async def on_ready() -> None:
        info = (
            f"[bold cyan]Usuario:[/bold cyan] {bot.user}\n"
            f"[bold cyan]PID:[/bold cyan] {os.getpid()}\n"
            f"[bold cyan]Guilds:[/bold cyan] {len(bot.guilds)}"
        )
        console.print(
            Panel(
                info,
                title="[bold green]ChenchoBot Online[/bold green]",
                expand=False,
            )
        )

    @bot.event
    async def on_guild_remove(guild: discord.Guild) -> None:
        """Limpia el estado del reproductor si el bot es expulsado de un servidor."""
        music_cog = bot.get_cog("Music")
        if music_cog and hasattr(music_cog, "players") and guild.id in music_cog.players:
            player = music_cog.players[guild.id]
            await player.disconnect()
            music_cog.remove_player(guild.id)
            logger.info(
                "Recursos liberados del servidor expulsado: %s (%s)",
                guild.name,
                guild.id,
            )

    return bot


def main() -> None:
    """Punto de entrada: valida la configuración y arranca el servicio."""
    setup_logging()
    settings = get_settings()

    # 1. Validación explícita de entorno antes de conectarse a Discord
    try:
        settings.validate_production()
    except (ConfigurationError, FileNotFoundError) as error:
        console.print(
            Panel(
                f"[bold red]{error}[/bold red]",
                title="Error de Configuración",
                border_style="red",
            )
        )
        sys.exit(1)

    # 2. Conversión segura del ID del servidor de desarrollo
    parsed_guild_id: int | None = None
    if settings.test_guild_id and settings.test_guild_id.strip():
        try:
            parsed_guild_id = int(settings.test_guild_id)
        except ValueError:
            logger.warning(
                "TEST_GUILD_ID no es un número válido: %r. Se sincronizará globalmente.",
                settings.test_guild_id,
            )

    # 3. Inicialización y ejecución
    bot = build_bot(test_guild_id=parsed_guild_id)
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
