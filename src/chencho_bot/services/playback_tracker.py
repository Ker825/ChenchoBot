import logging

from chencho_bot.database.repositories.stats_repository import TrackStatsRepository
from chencho_bot.database.session import async_session_factory
from chencho_bot.music.events import PlayerEventListener
from chencho_bot.music.models import Track

logger = logging.getLogger(__name__)


class PlaybackTracker(PlayerEventListener):
    """Observador que persiste las metricas al terminar una reproduccion."""

    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    async def on_track_start(self, track: Track) -> None:
        pass

    async def on_track_end(self, track: Track) -> None:
        try:
            async with async_session_factory() as session:
                repo = TrackStatsRepository(session)
                await repo.increment_play_count(self.guild_id, track)
                await session.commit()
                logger.info(
                    "TrackStat registrada: '%s' en guild %d",
                    track.title,
                    self.guild_id,
                )
        except Exception as error:
            logger.error("Error al persistir track_stat para '%s': %s", track.title, error)

    async def on_track_error(self, track: Track, error: Exception) -> None:
        pass

    async def on_queue_empty(self) -> None:
        pass
