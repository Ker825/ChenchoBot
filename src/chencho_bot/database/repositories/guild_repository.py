import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from chencho_bot.database.models import GuildConfig

logger = logging.getLogger(__name__)


class GuildRepository:
    """Implementacion asincrona del repositorio de configuraciones de servidor con PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, guild_id: int) -> GuildConfig | None:
        """Obtiene la configuracion de un servidor por su snowflake ID."""
        statement = select(GuildConfig).where(GuildConfig.guild_id == guild_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create(self, guild_id: int) -> GuildConfig:
        """
        Recupera la configuracion existente o inserta una por defecto.
        Utiliza ON CONFLICT DO NOTHING para mitigar condiciones de carrera concurrentes.
        """
        # 1. Intento de insercion segura con valores por defecto
        insert_stmt = (
            pg_insert(GuildConfig)
            .values(
                guild_id=guild_id,
                default_volume=100,
                autoplay_enabled=False,
                inactivity_timeout_seconds=180,
                updated_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["guild_id"])
        )
        await self.session.execute(insert_stmt)

        # 2. Obtencion de la entidad garantizada en la base de datos
        config = await self.get(guild_id)
        if config is None:
            raise RuntimeError(
                f"Fallo critico de persistencia: no se pudo obtener ni crear GuildConfig para {guild_id}"
            )
        return config

    async def update(
        self,
        guild_id: int,
        *,
        dj_role_id: int | None = None,
        music_channel_id: int | None = None,
        default_volume: int | None = None,
        autoplay_enabled: bool | None = None,
        inactivity_timeout_seconds: int | None = None,
    ) -> GuildConfig | None:
        """
        Actualiza selectivamente los campos proporcionados y refresca updated_at.
        Retorna la entidad actualizada o None si el servidor no existe.
        """
        values_to_update: dict[str, object] = {"updated_at": datetime.now(UTC)}

        # Filtrar solo los parametros explicitamente pasados (distintos de None en llamadas dirigidas)
        if dj_role_id is not None:
            values_to_update["dj_role_id"] = dj_role_id
        if music_channel_id is not None:
            values_to_update["music_channel_id"] = music_channel_id
        if default_volume is not None:
            values_to_update["default_volume"] = max(1, min(default_volume, 150))
        if autoplay_enabled is not None:
            values_to_update["autoplay_enabled"] = autoplay_enabled
        if inactivity_timeout_seconds is not None:
            values_to_update["inactivity_timeout_seconds"] = max(30, inactivity_timeout_seconds)

        statement = (
            update(GuildConfig)
            .where(GuildConfig.guild_id == guild_id)
            .values(**values_to_update)
            .returning(GuildConfig)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def set_dj_role(self, guild_id: int, role_id: int | None) -> GuildConfig | None:
        """Asigna o remueve el rol de DJ del servidor."""
        statement = (
            update(GuildConfig)
            .where(GuildConfig.guild_id == guild_id)
            .values(
                dj_role_id=role_id,
                updated_at=datetime.now(UTC),
            )
            .returning(GuildConfig)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete(self, guild_id: int) -> bool:
        """Elimina el registro de un servidor de la base de datos."""
        statement = delete(GuildConfig).where(GuildConfig.guild_id == guild_id)
        result = await self.session.execute(statement)
        return result.rowcount > 0
