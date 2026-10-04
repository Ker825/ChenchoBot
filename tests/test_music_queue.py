from chencho_bot.music.models import Track
from chencho_bot.music.queue import MusicQueue


def create_mock_track(title: str) -> Track:
    """Helper para crear instancias ligeras de Track para tests."""
    return Track(
        title=title,
        artist="Test Artist",
        album="Test Album",
        duration_ms=180_000,
        search_query=f"{title} Test Artist",
        spotify_url="https://spotify.com/track/123",
        cover_url="https://image.url",
        requester=None,
    )


def test_history_circular_buffer_maxlen():
    """Valida que el historial descarte elementos antiguos al superar maxlen."""
    queue = MusicQueue(max_history=3)
    tracks = [create_mock_track(f"T{i}") for i in range(5)]

    for t in tracks:
        queue.add_track(t)
        queue.get_next()

    history = queue.get_history()
    assert len(history) == 3
    assert [t.title for t in history] == ["T2", "T3", "T4"]


def test_queue_shuffle_maintains_items():
    """Comprueba que el shuffle conserve la totalidad de las canciones."""
    queue = MusicQueue()
    tracks = [create_mock_track(f"Track {i}") for i in range(10)]
    queue.add_tracks(tracks)

    assert queue.shuffle() is True
    assert len(queue) == 10
    assert set(t.title for t in queue.get_tracks()) == set(t.title for t in tracks)


def test_remove_by_valid_and_invalid_index():
    """Evalua la eliminacion defensiva por indice 0-indexed."""
    queue = MusicQueue()
    tracks = [create_mock_track("A"), create_mock_track("B"), create_mock_track("C")]
    queue.add_tracks(tracks)

    # Indice invalido
    assert queue.remove(-1) is None
    assert queue.remove(10) is None
    assert len(queue) == 3

    # Indice valido (eliminar 'B')
    removed = queue.remove(1)
    assert removed is not None
    assert removed.title == "B"
    assert [t.title for t in queue.get_tracks()] == ["A", "C"]


def test_move_track_positions():
    """Evalua mover una cancion de posicion origen a destino."""
    queue = MusicQueue()
    tracks = [create_mock_track("A"), create_mock_track("B"), create_mock_track("C")]
    queue.add_tracks(tracks)

    # Mover 'C' (indice 2) a la primera posicion (indice 0)
    assert queue.move(2, 0) is True
    assert [t.title for t in queue.get_tracks()] == ["C", "A", "B"]

    # Rango fuera de limites
    assert queue.move(0, 5) is False
