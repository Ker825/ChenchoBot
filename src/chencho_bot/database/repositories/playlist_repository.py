import logging
from typing import Protocol

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from chencho_bot.database.models import CustomPlaylist, PlaylistItem
from chencho_bot.music.models import Track

logger = logging.getLogger(__name__)


class PlaylistRepositoryProtocol(Protocol):
    """Contrato abstracto para la persistencia y gestion de listas personalizadas."""

    async def create_playlist(self, guild_id: int, creator_id: int, name: str) -> CustomPlaylist: ...

    async def get_playlist(self, guild_id: int, creator_id: int, name: str) -> CustomPlaylist | None: ...

    async def list_user_playlists(self, guild_id: int, creator_id: int) -> list[CustomPlaylist]: ...

    async def add_track(self, playlist_id: int, track: Track) -> PlaylistItem: ...

    async def remove_track(self, playlist_id: int, position: int) -> bool: ...

    async def delete_playlist(self, guild_id: int, creator_id: int, name: str) -> bool: ...


class PlaylistRepository:
    """Implementacion asincrona del repositorio de playlists con ordenamiento secuencial."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_playlist(
        self,
        guild_id: int,
        creator_id: int,
        name: str,
    ) -> CustomPlaylist:
        """Crea una lista de reproduccion asociada a un servidor y usuario creador."""
        playlist = CustomPlaylist(
            guild_id=guild_id,
            creator_id=creator_id,
            name=name.strip(),
        )
        self.session.add(playlist)
        await self.session.flush()
        return playlist

    async def get_playlist(
        self,
        guild_id: int,
        creator_id: int,
        name: str,
    ) -> CustomPlaylist | None:
        """Recupera la playlist con todas sus pistas cargadas en memoria (eager loading)."""
        statement = (
            select(CustomPlaylist)
            .where(
                CustomPlaylist.guild_id == guild_id,
                CustomPlaylist.creator_id == creator_id,
                CustomPlaylist.name == name.strip(),
            )
            .options(selectinload(CustomPlaylist.tracks))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_user_playlists(
        self,
        guild_id: int,
        creator_id: int,
    ) -> list[CustomPlaylist]:
        """Obtiene todas las listas creadas por un usuario en el servidor especificado."""
        statement = (
            select(CustomPlaylist)
            .where(
                CustomPlaylist.guild_id == guild_id,
                CustomPlaylist.creator_id == creator_id,
            )
            .order_by(CustomPlaylist.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_track(
        self,
        playlist_id: int,
        track: Track,
    ) -> PlaylistItem:
        """Calcula de forma atomica la siguiente posicion y anexa la pista."""
        max_pos_stmt = select(func.coalesce(func.max(PlaylistItem.position), 0)).where(
            PlaylistItem.playlist_id == playlist_id
        )
        max_pos_result = await self.session.execute(max_pos_stmt)
        next_position = max_pos_result.scalar_one() + 1

        item = PlaylistItem(
            playlist_id=playlist_id,
            title=track.title,
            artist=track.artist,
            search_query=track.search_query,
            spotify_url=track.spotify_url,
            duration_ms=track.duration_ms,
            position=next_position,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def remove_track(
        self,
        playlist_id: int,
        position: int,
    ) -> bool:
        """Elimina una pista por posicion y reindexa en cascada las posiciones subsiguientes."""
        delete_stmt = delete(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.position == position,
        )
        result = await self.session.execute(delete_stmt)
        if result.rowcount == 0:
            return False

        # Reajuste de posiciones para evitar huecos en la secuencia
        reorder_stmt = (
            update(PlaylistItem)
            .where(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.position > position,
            )
            .values(position=PlaylistItem.position - 1)
        )
        await self.session.execute(reorder_stmt)
        return True

    async def delete_playlist(
        self,
        guild_id: int,
        creator_id: int,
        name: str,
    ) -> bool:
        """Elimina la lista de reproduccion (las pistas asociadas caen por CASCADE)."""
        statement = delete(CustomPlaylist).where(
            CustomPlaylist.guild_id == guild_id,
            CustomPlaylist.creator_id == creator_id,
            CustomPlaylist.name == name.strip(),
        )
        result = await self.session.execute(statement)
        return result.rowcount > 0
