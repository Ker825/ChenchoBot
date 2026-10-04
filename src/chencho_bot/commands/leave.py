import discord
from discord import app_commands
from discord.ext import commands

from chencho_bot.music.player import MusicPlayer
from chencho_bot.utils.guards import VoiceGuard
from chencho_bot.utils.ui.discord_handler import DiscordUIHandler
from chencho_bot.utils.ui.embeds import build_status_embed


class Leave(commands.Cog):
    """Comando para desconectar al bot y liberar recursos de audio."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ui_handlers: dict[int, DiscordUIHandler] = {}
        self.players: dict[int, MusicPlayer] = {}

    def get_player(
        self,
        guild_id: int,
        channel: discord.abc.Messageable | None = None,
    ) -> MusicPlayer:
        """Obtiene o instancia el MusicPlayer vinculandolo a su DiscordUIHandler."""
        if guild_id not in self.players:
            player = MusicPlayer(self.bot)

            # Si se proporciona el canal de texto, se enlaza el adaptador de UI
            if channel:
                ui_handler = DiscordUIHandler(text_channel=channel, player=player)
                player.listener = ui_handler
                self.ui_handlers[guild_id] = ui_handler

            self.players[guild_id] = player

        return self.players[guild_id]

    def remove_player(self, guild_id: int) -> None:
        """Remueve las instancias de dominio y presentacion para liberar memoria."""
        self.players.pop(guild_id, None)
        self.ui_handlers.pop(guild_id, None)

    @app_commands.command(
        name="leave",
        description="Desconecta al bot del canal de voz y limpia la sesion activa.",
    )
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        # 1. Seguridad: Verificar que el usuario comparta el canal con el bot
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        assert interaction.guild is not None
        guild_id = interaction.guild.id

        if interaction.guild.voice_client is None:
            embed = build_status_embed(
                "No estoy en ningun canal de voz.",
                success=False,
            )
            await interaction.followup.send(embed=embed)
            return

        # 2. Desconexion defensiva si existe un reproductor registrado
        if guild_id in self.players:
            player = self.players[guild_id]
            await player.disconnect()
            self.remove_player(guild_id)
        else:
            # Fallback en caso de cliente de voz conectado sin player en memoria
            await interaction.guild.voice_client.disconnect()

        embed = build_status_embed(
            "Desconectado exitosamente y sesion reiniciada.",
            success=True,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leave(bot))
