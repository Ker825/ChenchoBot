import contextlib
import math

import discord

from chencho_bot.music.models import Track
from chencho_bot.utils.ui.embeds import build_queue_page_embed


class QueuePaginationView(discord.ui.View):
    """Componente interactivo para paginar la cola mediante botones."""

    def __init__(
        self,
        tracks: list[Track],
        per_page: int = 10,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.tracks = tracks
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, math.ceil(len(tracks) / per_page))
        self.message: discord.Message | None = None

        self._update_buttons()

    def _update_buttons(self) -> None:
        """Habilita o deshabilita botones segun los limites de navegacion."""
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages

    @discord.ui.button(
        label="\u25c0 Anterior",
        style=discord.ButtonStyle.secondary,
        custom_id="queue_prev_page",
    )
    async def prev_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self.current_page -= 1
        self._update_buttons()
        embed = build_queue_page_embed(
            self.tracks,
            current_page=self.current_page,
            per_page=self.per_page,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Siguiente \u25b6",
        style=discord.ButtonStyle.secondary,
        custom_id="queue_next_page",
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self.current_page += 1
        self._update_buttons()
        embed = build_queue_page_embed(
            self.tracks,
            current_page=self.current_page,
            per_page=self.per_page,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        """Inactiva los botones al expirar el tiempo de gracia."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
