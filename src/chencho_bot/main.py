import logging
import os
import sys

import discord
from discord.ext import commands
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from chencho_bot.config.settings import DISCORD_TOKEN
from chencho_bot.music.player import MusicPlayer
from chencho_bot.utils.logger import setup_logging

console = Console()
# 1. El nivel del handler/basicConfig debe ser DEBUG
logging.basicConfig(
    level=logging.DEBUG,  # Si está en INFO, descartará todo debug
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False,
        )
    ],
)

TEST_GUILD_ID = 1283613379982004297

intents = discord.Intents.default()
intents.message_content = True


class ChenchoBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
        )
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Obtiene o crea el reproductor de un servidor."""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self)
        return self.players[guild_id]

    async def setup_hook(self) -> None:
        extensions = [
            "chencho_bot.commands.ping",
            "chencho_bot.commands.music",
            "chencho_bot.commands.search",
            "chencho_bot.commands.join",
            "chencho_bot.commands.leave",
        ]

        table = Table(
            title="Carga de Extensiones", show_header=True, header_style="bold cyan"
        )
        table.add_column("Módulo", style="dim")
        table.add_column("Estado", justify="center")
        table.add_column("Detalle")

        for extension in extensions:
            try:
                await self.load_extension(extension)
                table.add_row(
                    extension, "[bold green]OK[/bold green]", "Cargada correctamente"
                )
            except Exception as error:
                table.add_row(extension, "[bold red]FAIL[/bold red]", str(error))

        console.print(table)

        guild = discord.Object(id=TEST_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)

        console.print(
            f"[bold blue]Tree Sync:[/bold blue] Sincronizados [bold yellow]{len(synced)}[/bold yellow] comandos en el servidor de pruebas."
        )


bot = ChenchoBot()


@bot.event
async def on_ready() -> None:
    info = (
        f"[bold cyan]Usuario:[/bold cyan] {bot.user}\n"
        f"[bold cyan]PID:[/bold cyan] {os.getpid()}\n"
        f"[bold cyan]Guilds:[/bold cyan] {len(bot.guilds)}"
    )
    console.print(
        Panel(info, title="[bold green]ChenchoBot Online[/bold green]", expand=False)
    )


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        console.print(
            Panel(
                "[bold red]DISCORD_TOKEN no encontrado en el entorno.[/bold red]",
                title="Error Crítico",
                border_style="red",
            )
        )
        sys.exit(1)

    bot.run(DISCORD_TOKEN)
    setup_logging()
