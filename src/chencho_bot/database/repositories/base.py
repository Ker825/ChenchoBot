from typing import Protocol

from chencho_bot.database.models import GuildConfig


class GuildRepositoryProtocol(Protocol):
    """Contrato abstracto para el acceso a datos de configuracion por servidor."""

    async def get(self, guild_id: int) -> GuildConfig | None: ...

    async def get_or_create(self, guild_id: int) -> GuildConfig: ...

    async def update(
        self,
        guild_id: int,
        dj_role_id: int | None = None,
        music_channel_id: int | None = None,
        default_volume: int | None = None,
        autoplay_enabled: bool | None = None,
        inactivity_timeout_seconds: int | None = None,
    ) -> GuildConfig | None: ...

    async def delete(self, guild_id: int) -> bool: ...
