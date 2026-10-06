import contextlib
import math

import discord

from chencho_bot.music.models import Track
from chencho_bot.music.queue import MusicQueue


class QueuePaginationView(discord.ui.View):
    """Vista interactiva con paginacion para visualizar la cola de reproduccion."""

    ITEMS_PER_PAGE: int = 5

    def __init__(
        self,
        queue: MusicQueue,
        requester: discord.User | discord.Member,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.queue = queue
        self.requester = requester
        self.current_page: int = 0
        self.message: discord.Message | None = None

        self._update_buttons()

    @property
    def total_pages(self) -> int:
        total_items = len(self.queue)
        if total_items == 0:
            return 1
        return math.ceil(total_items / self.ITEMS_PER_PAGE)

    def _update_buttons(self) -> None:
        """Sincroniza el estado activo o inactivo de la botonera de navegacion."""
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def build_embed(self) -> discord.Embed:
        """Construye la tarjeta visual representativa de la pagina activa."""
        tracks: list[Track] = self.queue.get_tracks()
        total_items = len(tracks)

        embed = discord.Embed(
            title="Cola de Reproduccion",
            color=0x1DB954,
        )

        if not tracks:
            embed.description = "La cola esta vacia."
            embed.set_footer(text="Pagina 1 de 1")
            return embed

        start_idx = self.current_page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        page_items = tracks[start_idx:end_idx]

        description_lines: list[str] = []
        for idx, track in enumerate(page_items, start=start_idx + 1):
            duration_sec = track.duration_ms // 1000
            mins, secs = divmod(duration_sec, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            description_lines.append(f"`{idx}.` **{track.title}** - {track.artist} (`{time_str}`)")

        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"Pagina {self.current_page + 1} de {self.total_pages} | Total: {total_items} canciones")
        return embed

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "No tienes permisos para navegar en este menu.",
                ephemeral=True,
            )
            return

        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self,
            )

    @discord.ui.button(label="Siguiente ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "No tienes permisos para navegar en este menu.",
                ephemeral=True,
            )
            return

        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self,
            )

    async def on_timeout(self) -> None:
        """Desactiva los botones y actualiza el mensaje tras la expiracion de inactividad."""
        # 1. Deshabilitar los componentes visuales de la vista
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

        # 2. Edicion segura con proteccion de referencias y excepciones de red
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
