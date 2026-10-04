from typing import TYPE_CHECKING

import discord

from chencho_bot.utils.guards import VoiceGuard
from chencho_bot.utils.ui.embeds import build_status_embed

if TYPE_CHECKING:
    from chencho_bot.music.player import MusicPlayer

# Secuencias Unicode para controles multimedia (sin emojis literales en el codigo)
ICON_PREV = "\u23ee"  # ⏮
ICON_PLAY_PAUSE = "\u23ef"  # ⏯
ICON_SKIP = "\u23ed"  # ⏭
ICON_SHUFFLE = "\U0001f500"  # 🔀
ICON_LOOP = "\U0001f501"  # 🔁
ICON_STOP = "\u23f9"  # ⏹


class PlayerControlsView(discord.ui.View):
    """Panel interactivo de control de audio con distribucion simetrica 3x2 y estado reactivo."""

    def __init__(self, player: "MusicPlayer", timeout: float | None = None) -> None:
        super().__init__(timeout=timeout)
        self.player = player
        self.sync_button_states()

    def sync_button_states(self) -> None:
        """Ajusta estilos visuales y disponibilidad segun el estado real del reproductor."""
        # Estado de repeticion (Loop)
        is_loop = bool(self.player.current_track and self.player.current_track.loop)
        self.loop_button.style = discord.ButtonStyle.primary if is_loop else discord.ButtonStyle.secondary

        # Estado de reproduccion / pausa
        self.play_pause_button.style = (
            discord.ButtonStyle.success if self.player.is_paused else discord.ButtonStyle.secondary
        )

        # Restricciones operativas defensivas
        self.prev_button.disabled = not self.player.queue.has_previous()
        self.shuffle_button.disabled = len(self.player.queue) <= 1
        self.skip_button.disabled = not self.player.is_playing and not self.player.is_paused

    def disable_all(self) -> None:
        """Inhabilita todos los componentes interactivos de la tarjeta."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    # -------------------------------------------------------------------------
    # FILA 0: Transporte de Audio (Anterior, Play/Pause, Siguiente)
    # -------------------------------------------------------------------------

    @discord.ui.button(
        emoji=ICON_PREV,
        style=discord.ButtonStyle.secondary,
        row=0,
        custom_id="player_controls_prev",
    )
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        if self.player.previous():
            self.sync_button_states()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message(
                "No hay pistas previas en el historial.",
                ephemeral=True,
            )

    @discord.ui.button(
        emoji=ICON_PLAY_PAUSE,
        style=discord.ButtonStyle.secondary,
        row=0,
        custom_id="player_controls_play_pause",
    )
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        if self.player.is_paused:
            self.player.resume()
        elif self.player.is_playing:
            self.player.pause()

        self.sync_button_states()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        emoji=ICON_SKIP,
        style=discord.ButtonStyle.secondary,
        row=0,
        custom_id="player_controls_skip",
    )
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        if self.player.skip():
            self.sync_button_states()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message(
                "No hay ninguna pista en reproduccion.",
                ephemeral=True,
            )

    # -------------------------------------------------------------------------
    # FILA 1: Modificadores y Sesion (Shuffle, Loop, Stop)
    # -------------------------------------------------------------------------

    @discord.ui.button(
        emoji=ICON_SHUFFLE,
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="player_controls_shuffle",
    )
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        if self.player.queue.shuffle():
            self.sync_button_states()
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                "Cola de reproduccion mezclada.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "No hay suficientes canciones para mezclar la cola.",
                ephemeral=True,
            )

    @discord.ui.button(
        emoji=ICON_LOOP,
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="player_controls_loop",
    )
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        self.player.loop()
        self.sync_button_states()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        emoji=ICON_STOP,
        style=discord.ButtonStyle.danger,
        row=1,
        custom_id="player_controls_stop",
    )
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await VoiceGuard.ensure_same_channel(interaction):
            return

        self.player.stop()
        self.disable_all()
        await interaction.response.edit_message(view=self)
        embed = build_status_embed(
            message="Reproduccion detenida y cola limpiada.",
            success=False,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
