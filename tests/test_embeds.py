from chencho_bot.music.models import Track
from chencho_bot.utils.ui.embeds import (
    build_now_playing_embed,
    format_time,
    generate_progress_bar,
)


def test_format_time_handles_zero_negative_and_hours():
    assert format_time(0) == "00:00"
    assert format_time(-5000) == "00:00"
    assert format_time(65000) == "01:05"
    assert format_time(3665000) == "01:01:05"


def test_generate_progress_bar_edge_cases():
    # Duracion cero o negativa
    empty_bar = generate_progress_bar(current_ms=1000, total_ms=0)
    assert "`00:00`" in empty_bar

    # Progreso normal (50%)
    half_bar = generate_progress_bar(current_ms=30000, total_ms=60000, bar_length=10)
    assert "\u25cf" in half_bar

    # Tiempo actual mayor al total (clamping)
    overflow_bar = generate_progress_bar(current_ms=90000, total_ms=60000, bar_length=10)
    assert overflow_bar.endswith("`-00:00`")


def test_build_now_playing_embed_without_requester():
    track = Track(
        title="test title",
        artist="Test Artist",
        album="Test Album",
        duration_ms=180_000,
        search_query="Test Artist",
        spotify_url="https://open.spotify.com/intl-es/track/1Gv0kOO9NShEjMeqJSpC99?si=8cfe03498c2e4341",
        cover_url=None,
        requester=None,
    )
    embed = build_now_playing_embed(track, current_ms=60000)
    assert embed.footer.text == "Recomendado automaticamente por Autoplay (YouTube Music)"
    assert embed.thumbnail.url is None
    assert "test title" in embed.description
