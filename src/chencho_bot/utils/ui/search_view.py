import contextlib

import discord
from discord.ext import commands

from chencho_bot.music.models import Track
from chencho_bot.utils.ui.embeds import build_status_embed


class SearchSelectView(discord.ui.View):
    """Vista interactiva con menu desplegable para seleccionar pistas encontradas."""

    def __init__(
        self,
        tracks: list[Track],
        bot: commands.Bot,
        guild_id: int,
        requester: discord.Member,
    ) -> None:
        super().__init__(timeout=60.0)
        self.tracks = tracks
        self.bot = bot
        self.guild_id = guild_id
        self.requester = requester
        self.message: discord.Message | None = None

        options = [
            discord.SelectOption(
                label=track.title[:100],
                description=f"{track.artist} | {track.album}"[:100],
                value=str(idx),
            )
            for idx, track in enumerate(tracks[:10])
        ]

        self.select_menu = discord.ui.Select(
            placeholder="Selecciona una cancion para reproducir...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.select_menu.callback = self._on_select
        self.add_item(self.select_menu)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "Solo el usuario que inicio la busqueda puede interactuar.",
                ephemeral=True,
            )
            return

        selected_idx = int(self.select_menu.values[0])
        chosen_track = self.tracks[selected_idx]

        music_cog = self.bot.get_cog("Music")
        if not music_cog or not hasattr(music_cog, "get_player"):
            embed = build_status_embed(
                "El servicio de musica no esta disponible.",
                success=False,
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        player = music_cog.get_player(self.guild_id, channel=interaction.channel)
        player.queue.add_track(chosen_track)

        self.stop()
        embed = build_status_embed(
            f"Anadida a la cola: **{chosen_track.title}** de **{chosen_track.artist}**.",
            success=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

        if not player.is_playing:
            await player.play_next()

    async def on_timeout(self) -> None:
        self.select_menu.disabled = True
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
