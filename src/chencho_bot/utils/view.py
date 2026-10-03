from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from chencho_bot.music.player import MusicPlayer

# Secuencias Unicode para controles multimedia (sin emojis en el codigo)
ICON_LOOP = "\U0001f501"
ICON_PREV = "\u23ee"  # Anterior
ICON_PLAY_PAUSE = "\u23ef"  # Play / Pausa
ICON_SKIP = "\u23ed"  # Siguiente
ICON_STOP = "\u23f9"  # Detener


class PlayerControlsView(discord.ui.View):
    def __init__(self, player: "MusicPlayer") -> None:
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(emoji=ICON_LOOP, style=discord.ButtonStyle.secondary, row=0)
    async def loop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.player.loop()
        await interaction.response.send_message(
            "Modo repeticion alternado", ephemeral=True
        )

    @discord.ui.button(emoji=ICON_PREV, style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.player.previous()
        await interaction.response.send_message(
            "Reproduciendo pista anterior", ephemeral=True
        )

    @discord.ui.button(
        emoji=ICON_PLAY_PAUSE, style=discord.ButtonStyle.secondary, row=0
    )
    async def play_pause_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.player.voice_client and self.player.voice_client.is_paused():
            self.player.resume()
            await interaction.response.send_message("Reanudado", ephemeral=True)
        else:
            self.player.pause()
            await interaction.response.send_message("Pausado", ephemeral=True)

    @discord.ui.button(emoji=ICON_SKIP, style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.player.skip()
        await interaction.response.send_message("Saltada", ephemeral=True)

    @discord.ui.button(emoji=ICON_STOP, style=discord.ButtonStyle.secondary, row=0)
    async def stop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.player.stop()
        await interaction.response.send_message("Detenido", ephemeral=True)
