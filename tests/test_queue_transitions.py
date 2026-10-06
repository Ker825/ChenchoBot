from chencho_bot.music.models import Track
from chencho_bot.music.queue import MusicQueue


def _create_dummy_track(title: str) -> Track:
    return Track(
        title=title,
        artist="Artist",
        album="Album",
        spotify_url=f"https://open.spotify.com/track/{title}",
        search_query=f"{title} Artist audio",
        duration_ms=180000,
        requester=None,
    )


def test_move_current_removes_track_from_history() -> None:
    queue = MusicQueue()
    track_a = _create_dummy_track("A")
    track_b = _create_dummy_track("B")
    track_c = _create_dummy_track("C")

    queue.add_track(track_a)
    queue.add_track(track_b)
    queue.add_track(track_c)

    # 1. Simular inicio de reproduccion de A
    current = queue.get_next()
    assert current is track_a
    assert queue.get_history() == [track_a]
    assert [t.title for t in queue.get_tracks()] == ["B", "C"]

    # 2. Mover A a la posicion 3 de la cola (indice 2)
    success = queue.move_current(current, 2)
    assert success is True

    # Invariante: A no debe estar en historial y debe estar al final de queue
    assert queue.get_history() == []
    assert [t.title for t in queue.get_tracks()] == ["B", "C", "A"]


def test_previous_after_move_current() -> None:
    queue = MusicQueue()
    track_prev = _create_dummy_track("Prev")
    track_a = _create_dummy_track("A")
    track_b = _create_dummy_track("B")

    # 1. Reproducir pista previa para poblar historial real
    queue.add_track(track_prev)
    queue.add_track(track_a)
    queue.add_track(track_b)

    completed_prev = queue.get_next()
    assert completed_prev is track_prev

    # 2. Reproducir A
    current_a = queue.get_next()
    assert current_a is track_a
    assert queue.get_history() == [track_prev, track_a]

    # 3. Mover A al final de la cola (indice 1)
    queue.move_current(current_a, 1)
    assert queue.get_history() == [track_prev]
    assert [t.title for t in queue.get_tracks()] == ["B", "A"]

    # 4. Iniciar B
    current_b = queue.get_next()
    assert current_b is track_b
    assert queue.get_history() == [track_prev, track_b]

    # 5. Ejecutar previous() mientras B suena
    recovered = queue.get_previous(current_b)

    # Debe retornar track_prev (no A) y reubicar B al frente
    assert recovered is track_prev
    assert [t.title for t in queue.get_tracks()] == ["B", "A"]
