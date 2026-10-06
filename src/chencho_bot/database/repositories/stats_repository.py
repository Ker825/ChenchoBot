import logging
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from chencho_bot.database.models import TrackStat
from chencho_bot.music.models import Track

logger = logging.getLogger(__name__)


class TrackStatsRepository:
    """Gestiona el conteo de reproducciones y metricas musicales en PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def increment_play_count(self, guild_id: int, track: Track) -> None:
        """Incrementa atomicamente el contador o inserta el registro inicial."""
        statement = (
            pg_insert(TrackStat)
            .values(
                guild_id=guild_id,
                title=track.title.strip(),
                artist=track.artist.strip(),
                spotify_url=track.spotify_url,
                play_count=1,
                last_played_at=datetime.now(UTC),
            )
            .on_conflict_do_update(
                constraint="uq_guild_track_stat",
                set_={
                    "play_count": TrackStat.play_count + 1,
                    "last_played_at": datetime.now(UTC),
                    "spotify_url": track.spotify_url or TrackStat.spotify_url,
                },
            )
        )
        await self.session.execute(statement)

    async def get_top_tracks(self, guild_id: int, limit: int = 10) -> list[TrackStat]:
        """Obtiene las canciones con mayor cantidad de reproducciones en el servidor."""
        statement = (
            select(TrackStat).where(TrackStat.guild_id == guild_id).order_by(desc(TrackStat.play_count)).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
