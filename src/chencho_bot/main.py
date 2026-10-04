import logging
import os
import sys

import discord
from discord.ext import commands
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from chencho_bot.config.settings import DISCORD_TOKEN, TEST_GUILD_ID
from chencho_bot.music.player import MusicPlayer
from chencho_bot.utils.logger import setup_logging

logger = logging.getLogger(__name__)
console = Console()

EXTENSIONS_TO_LOAD: tuple[str, ...] = (
    "chencho_bot.commands.ping",
    "chencho_bot.commands.music",
    "chencho_bot.commands.search",
    "chencho_bot.commands.join",
    "chencho_bot.commands.leave",
)


class ChenchoBot(commands.Bot):
    """Cliente principal del bot con gestion centralizada de reproductores."""

    def __init__(self, test_guild_id: int | None = None) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )
        self.test_guild_id: int | None = test_guild_id
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Obtiene o inicializa el reproductor musical para un servidor."""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(bot=self)
        return self.players[guild_id]

    def remove_player(self, guild_id: int) -> MusicPlayer | None:
        """Elimina el reproductor del registro para evitar fugas de memoria."""
        return self.players.pop(guild_id, None)

    async def setup_hook(self) -> None:
        """Carga de extensiones modulares y sincronizacion selectiva de comandos."""
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
                logger.exception("Error al cargar la extension: %s", extension)
                table.add_row(
                    extension,
                    "[bold red]FAIL[/bold red]",
                    str(error),
                )

        console.print(table)

        # Sincronizacion restringida al servidor de desarrollo si esta configurado
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


def build_bot() -> ChenchoBot:
    """Fabrica para instanciar el cliente con sus listeners y configuracion."""
    bot = ChenchoBot(test_guild_id=TEST_GUILD_ID)

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
        """Limpia el estado y los recursos si el bot es expulsado de un servidor."""
        player = bot.remove_player(guild.id)
        if player:
            await player.disconnect()
            logger.info(
                "Recursos liberados del servidor: %s (%s)", guild.name, guild.id
            )

    return bot


def main() -> None:
    """Punto de entrada principal para el inicio de la aplicacion."""
    setup_logging()

    if not DISCORD_TOKEN:
        console.print(
            Panel(
                "[bold red]DISCORD_TOKEN no encontrado en el entorno.[/bold red]",
                title="Error Critico",
                border_style="red",
            )
        )
        sys.exit(1)

    bot = build_bot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
