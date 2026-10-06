import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from chencho_bot.database.models import GuildConfig
from chencho_bot.database.repositories.guild_repository import GuildRepository
from chencho_bot.database.session import async_session_factory

logger = logging.getLogger(__name__)


class GuildConfigService:
    """Servicio para la administracion y cache en memoria de configuraciones por servidor."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or async_session_factory
        self._cache: dict[int, GuildConfig] = {}

    async def get_config(self, guild_id: int) -> GuildConfig:
        """Recupera la configuracion desde la cache o la obtiene/crea en PostgreSQL."""
        if guild_id in self._cache:
            return self._cache[guild_id]

        async with self._session_factory() as session:
            repo = GuildRepository(session)
            config = await repo.get_or_create(guild_id)
            await session.commit()
            self._cache[guild_id] = config
            return config

    async def set_dj_role(self, guild_id: int, role_id: int | None) -> GuildConfig | None:
        """Actualiza el rol de DJ en la base de datos y sincroniza la cache."""
        async with self._session_factory() as session:
            repo = GuildRepository(session)
            updated = await repo.set_dj_role(guild_id, role_id)
            if updated is not None:
                await session.commit()
                self._cache[guild_id] = updated
                logger.info(
                    "Rol DJ actualizado para el servidor %s: %s",
                    guild_id,
                    role_id,
                )
            return updated

    async def update_config(
        self,
        guild_id: int,
        **kwargs: object,
    ) -> GuildConfig | None:
        """Actualiza selectivamente parametros de configuracion y refresca la cache."""
        async with self._session_factory() as session:
            repo = GuildRepository(session)
            updated = await repo.update(guild_id, **kwargs)
            if updated is not None:
                await session.commit()
                self._cache[guild_id] = updated
            return updated

    def invalidate(self, guild_id: int) -> None:
        """Invalida la entrada de un servidor en memoria para forzar lectura desde BD."""
        self._cache.pop(guild_id, None)
