from typing import Protocol

from chencho_bot.music.models import Track


class PlayerEventListener(Protocol):
    """Contrato de eventos emitidos por el reproductor musical."""

    async def on_track_start(self, track: Track) -> None:
        """Notifica el inicio de reproduccion de una pista."""
        ...

    async def on_track_error(self, track: Track, error: Exception) -> None:
        """Notifica un fallo critico durante el streaming."""
        ...

    async def on_queue_empty(self) -> None:
        """Notifica que la cola ha quedado sin pistas por reproducir."""
        ...
