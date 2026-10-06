from typing import Protocol

from chencho_bot.music.models import Track


class PlayerEventListener(Protocol):
    """Contrato de eventos emitidos por el reproductor musical."""

    async def on_track_start(self, track: Track) -> None: ...

    async def on_track_end(self, track: Track) -> None: ...

    async def on_track_error(self, track: Track, error: Exception) -> None: ...

    async def on_queue_empty(self) -> None: ...


class CompositePlayerListener:
    """Distribuye eventos a multiples observadores."""

    def __init__(self, listeners: list[PlayerEventListener] | None = None) -> None:
        self.listeners: list[PlayerEventListener] = listeners or []

    def add_listener(self, listener: PlayerEventListener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    async def on_track_start(self, track: Track) -> None:
        for listener in self.listeners:
            await listener.on_track_start(track)

    async def on_track_end(self, track: Track) -> None:
        for listener in self.listeners:
            await listener.on_track_end(track)

    async def on_track_error(self, track: Track, error: Exception) -> None:
        for listener in self.listeners:
            await listener.on_track_error(track, error)

    async def on_queue_empty(self) -> None:
        for listener in self.listeners:
            await listener.on_queue_empty()
