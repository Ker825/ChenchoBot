from unittest.mock import MagicMock, patch

import discord
import pytest

from chencho_bot.music.models import Track
from chencho_bot.services.resolver import TrackResolver


@pytest.fixture
def resolver():
    return TrackResolver()


@pytest.mark.asyncio
async def test_resolve_album_url(resolver):
    """Verifica que una URL de album extraiga multiples pistas y mantenga el requester."""
    mock_member = MagicMock(spec=discord.Member)
    mock_tracks_data = [
        {
            "title": f"Song {i}",
            "artist": "Album Artist",
            "album": "Great Album",
            "url": f"https://open.spotify.com/track/{i}",
            "cover_url": "https://image.com/cover.jpg",
            "duration_ms": 180000,
        }
        for i in range(5)
    ]

    with patch("chencho_bot.services.resolver.get_album_tracks", return_value=mock_tracks_data) as mock_get_album:
        url = "https://open.spotify.com/intl-es/album/4m2880jivSbbyEGAKfITCa"
        result = await resolver.resolve(url, requester=mock_member)

        mock_get_album.assert_called_once_with("4m2880jivSbbyEGAKfITCa")
        assert len(result) == 5
        assert isinstance(result[0], Track)
        assert result[0].album == "Great Album"
        assert result[0].cover_url == "https://image.com/cover.jpg"
        assert result[0].requester == mock_member


@pytest.mark.asyncio
async def test_resolve_artist_url(resolver):
    """Verifica que una URL de artista invoque get_artist_top_tracks."""
    mock_tracks_data = [
        {
            "title": "Hit Song",
            "artist": "Famous Artist",
            "album": "Best Of",
            "url": "https://open.spotify.com/track/hit",
            "cover_url": "https://image.com/artist.jpg",
            "duration_ms": 200000,
        }
    ]

    with patch("chencho_bot.services.resolver.get_artist_top_tracks", return_value=mock_tracks_data) as mock_get_artist:
        url = "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02"
        result = await resolver.resolve(url, requester=None)

        mock_get_artist.assert_called_once_with("06HL4z0CvFAxyc27GXpf02")
        assert len(result) == 1
        assert result[0].title == "Hit Song"
