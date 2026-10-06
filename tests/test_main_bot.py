from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from chencho_bot.commands.music import Music
from chencho_bot.main import ChenchoBot


@pytest.fixture
def bot_instance():
    return ChenchoBot(test_guild_id=123456789)


@pytest.fixture
def music_cog(bot_instance):
    return Music(bot_instance)


def test_get_player_creates_and_caches_instance(music_cog):
    """Verifica la inicializacion lazy y reuso del reproductor por servidor."""
    player_1 = music_cog.get_player(guild_id=1)
    player_2 = music_cog.get_player(guild_id=1)

    assert player_1 is player_2
    assert 1 in music_cog.players


def test_remove_player_cleans_cache(music_cog):
    """Verifica que remove_player libere la referencia del servidor."""
    player = music_cog.get_player(guild_id=1)

    removed_player = music_cog.remove_player(guild_id=1)

    assert removed_player is player
    assert 1 not in music_cog.players
    assert music_cog.remove_player(guild_id=1) is None


@pytest.mark.asyncio
async def test_on_guild_remove_triggers_disconnect(music_cog):
    """Verifica que salir de un servidor desconecte su reproductor."""
    mock_player = AsyncMock()

    music_cog.players[999] = mock_player

    guild = MagicMock(spec=discord.Guild)
    guild.id = 999
    guild.name = "Test Guild"

    await music_cog.on_guild_remove(guild)

    assert 999 not in music_cog.players
    mock_player.disconnect.assert_awaited_once()
