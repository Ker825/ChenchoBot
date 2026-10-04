from chencho_bot.services.spotify import _format_track, extract_spotify_resource


def test_extract_spotify_resource_variants():
    """Verifica la extraccion de IDs en URLs estandar, regionales y URIs."""
    # Track estandar con parametros de tracking
    res = extract_spotify_resource("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc123xyz")
    assert res == ("track", "4cOdK2wGLETKBW3PvgPWqT")

    # Album con prefijo internacional
    res = extract_spotify_resource("https://open.spotify.com/intl-es/album/2noRn2Aes5aoNVsU6iWThc")
    assert res == ("album", "2noRn2Aes5aoNVsU6iWThc")

    # Artista con esquema URI
    res = extract_spotify_resource("spotify:artist:06HL4z0CvFAxyc27GXpf02")
    assert res == ("artist", "06HL4z0CvFAxyc27GXpf02")

    # Texto no correspondiente a Spotify
    assert extract_spotify_resource("Queen Bohemian Rhapsody") is None


def test_format_track_inherits_album_metadata():
    """Valida la asignacion de portada y nombre por defecto para elementos de albumes."""
    raw_album_item = {
        "name": "Track Inside Album",
        "artists": [{"name": "Lead Artist"}],
        "external_urls": {"spotify": "https://open.spotify.com/track/123"},
        "duration_ms": 200000,
        # Nota: en items de album_tracks no viene la clave 'album'
    }

    formatted = _format_track(
        raw_album_item,
        default_album="Greatest Hits",
        default_cover_url="https://image.spotify.com/cover.jpg",
    )

    assert formatted is not None
    assert formatted["title"] == "Track Inside Album"
    assert formatted["album"] == "Greatest Hits"
    assert formatted["cover_url"] == "https://image.spotify.com/cover.jpg"
