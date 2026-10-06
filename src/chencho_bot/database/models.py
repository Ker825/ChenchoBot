from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GuildConfig(Base):
    """Configuración persistente por servidor."""

    __tablename__ = "guild_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dj_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    music_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    default_volume: Mapped[int] = mapped_column(SmallInteger, default=100)
    autoplay_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    inactivity_timeout_seconds: Mapped[int] = mapped_column(Integer, default=180)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    playlists: Mapped[list["CustomPlaylist"]] = relationship(
        back_populates="guild",
        cascade="all, delete-orphan",
    )


class CustomPlaylist(Base):
    """Listas de reproducción guardadas por usuarios en un servidor."""

    __tablename__ = "custom_playlists"
    __table_args__ = (UniqueConstraint("guild_id", "creator_id", "name", name="uq_guild_creator_playlist_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guild_configs.guild_id", ondelete="CASCADE"),
        index=True,
    )
    creator_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    guild: Mapped["GuildConfig"] = relationship(back_populates="playlists")
    tracks: Mapped[list["PlaylistItem"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.position",
    )


class PlaylistItem(Base):
    """Pistas asociadas a una lista personalizada."""

    __tablename__ = "playlist_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("custom_playlists.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    artist: Mapped[str] = mapped_column(String(255))
    search_query: Mapped[str] = mapped_column(Text)
    spotify_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)

    playlist: Mapped["CustomPlaylist"] = relationship(back_populates="tracks")


class TrackStat(Base):
    """Estadisticas y conteo acumulado de reproducciones por servidor."""

    __tablename__ = "track_stats"
    __table_args__ = (UniqueConstraint("guild_id", "title", "artist", name="uq_guild_track_stat"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guild_configs.guild_id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str] = mapped_column(String(255), index=True)
    spotify_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    play_count: Mapped[int] = mapped_column(Integer, default=1)
    last_played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
