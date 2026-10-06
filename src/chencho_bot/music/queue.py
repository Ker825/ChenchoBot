import random
from collections import deque
from collections.abc import Iterable

from chencho_bot.music.models import Track


class MusicQueue:
    """Gestiona la cola de reproduccion FIFO y el buffer circular de historial."""

    def __init__(self, max_history: int = 50) -> None:
        """Inicializa la cola con un limite maximo para el historial circular."""
        self._queue: deque[Track] = deque()
        self._history: deque[Track] = deque(maxlen=max_history)

    def add_track(self, track: Track) -> None:
        """Agrega una cancion al final de la cola."""
        self._queue.append(track)

    def add_tracks(self, tracks: Iterable[Track]) -> None:
        """Agrega multiples canciones en lote al final de la cola."""
        self._queue.extend(tracks)

    def get_next(self) -> Track | None:
        """Extrae la siguiente pista de la cola y la registra en el historial."""
        if not self._queue:
            return None

        track = self._queue.popleft()
        self._history.append(track)
        return track

    def get_previous(self, current_track: Track | None = None) -> Track | None:
        """Recupera la pista previa del historial y reubica la actual al frente de la cola."""
        if not self._history:
            return None

        # Si la pista actual ya estaba en la cima del historial, se retira primero
        if current_track is not None and self._history and self._history[-1] is current_track:
            self._history.pop()

        if not self._history:
            return None

        previous_track = self._history.pop()

        if current_track is not None:
            self._queue.appendleft(current_track)

        return previous_track

    def shuffle(self) -> bool:
        """Mezcla aleatoriamente las pistas pendientes en la cola."""
        if len(self._queue) <= 1:
            return False

        track_list = list(self._queue)
        random.shuffle(track_list)
        self._queue = deque(track_list)
        return True

    def remove(self, index: int) -> Track | None:
        """Elimina y retorna una pista por su indice (0-indexed)."""
        if not (0 <= index < len(self._queue)):
            return None

        track_list = list(self._queue)
        removed_track = track_list.pop(index)
        self._queue = deque(track_list)
        return removed_track

    def move(self, from_index: int, to_index: int) -> bool:
        """Mueve una pista desde una posicion origen a una destino (0-indexed)."""
        queue_len = len(self._queue)
        if not (0 <= from_index < queue_len and 0 <= to_index < queue_len):
            return False

        if from_index == to_index:
            return True

        track_list = list(self._queue)
        track = track_list.pop(from_index)
        track_list.insert(to_index, track)
        self._queue = deque(track_list)
        return True

    def move_current(self, track: Track, to_index: int) -> bool:
        """Reubica la pista activa en la cola de espera y la remueve del historial."""
        # 1. Limite valido: puede insertarse desde 0 hasta el final de la cola (len)
        if not (0 <= to_index <= len(self._queue)):
            return False

        # 2. Retirar del historial para evitar duplicados en previous()
        if self._history and self._history[-1] is track:
            self._history.pop()

        # 3. Insertar en la posicion solicitada
        self._queue.insert(to_index, track)
        return True

    def insert(self, index: int, track: Track) -> bool:
        """Inserta una pista en una posicion arbitraria de la cola (0-indexed)."""

        # Permite insertar desde el indice 0 hasta el final (len)
        if not (0 <= index <= len(self._queue)):
            return False

        self._queue.insert(index, track)
        return True

    def get(self, index: int) -> Track | None:
        """Obtiene una pista por indice sin eliminarla."""

        if not (0 <= index < len(self._queue)):
            return None

        return self._queue[index]

    def clear(self) -> None:
        """Vacia por completo la cola de pistas pendientes."""
        self._queue.clear()

    def clear_history(self) -> None:
        """Limpia el buffer de historial de reproduccion."""
        self._history.clear()

    def get_tracks(self) -> list[Track]:
        """Retorna una instantanea de las pistas actualmente en cola."""
        return list(self._queue)

    def get_history(self) -> list[Track]:
        """Retorna una instantanea de las pistas registradas en el historial."""
        return list(self._history)

    def is_empty(self) -> bool:
        """Indica si la cola no tiene canciones pendientes."""
        return len(self._queue) == 0

    def has_previous(self) -> bool:
        """Indica si existen pistas registradas en el historial."""
        return len(self._history) > 0

    def __len__(self) -> int:
        """Retorna la cantidad total de canciones en la cola."""
        return len(self._queue)
