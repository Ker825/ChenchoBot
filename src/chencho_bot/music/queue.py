from collections import deque

from chencho_bot.music.models import Track


class MusicQueue:
    """Cola FIFO de canciones."""

    def __init__(self) -> None:
        self._queue: deque[Track] = deque()
        self._history: deque[Track] = deque()
        self._play_previous = False

    def add_track(self, track: Track) -> None:
        """Añade una canción al final de la cola."""
        self._queue.append(track)

    def get_next(self) -> Track | None:
        """Extrae la siguiente canción y la añade al historial."""
        if self.is_empty():
            return None

        track = self._queue.popleft()
        self._history.append(track)

        return track

    def get_tracks(self) -> list[Track]:
        """Devuelve una copia de las canciones pendientes."""
        return list(self._queue)

    def is_empty(self) -> bool:
        """Indica si la cola está vacía."""
        return not self._queue

    def clear(self) -> None:
        """Vacía completamente la cola."""
        self._queue.clear()

    def __len__(self) -> int:
        """Devuelve el número de canciones pendientes."""
        return len(self._queue)

    def has_previous(self) -> bool:
        """Indica si hay canciones reproducidas anteriormente."""
        return bool(self._history)

    def get_previous(self, current_track: Track | None) -> Track | None:
        """Obtiene la canción anterior del historial."""

        if not self._history:
            return None

        # Si la canción actual es la última del historial,
        # la quitamos antes de buscar la anterior.
        if (
            current_track is not None
            and self._history
            and self._history[-1] is current_track
        ):
            self._history.pop()

        if not self._history:
            return None

        previous_track = self._history.pop()

        # La canción actual vuelve al principio de la cola.
        if current_track is not None:
            self._queue.appendleft(current_track)

        return previous_track

    def move_to_previous(self) -> Track | None:
        """Devuelve la última canción reproducida."""
        if not self._history:
            return None

        return self._history.pop()
