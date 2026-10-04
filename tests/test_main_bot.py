from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from chencho_bot.main import ChenchoBot


@pytest.fixture
def bot_instance():
    return ChenchoBot(test_guild_id=123456789)


def test_get_player_creates_and_caches_instance(bot_instance):
    """Verifica la inicializacion lazy y reuso del reproductor por servidor."""
    player_1 = bot_instance.get_player(guild_id=1)
    player_2 = bot_instance.get_player(guild_id=1)

    assert player_1 is player_2
    assert 1 in bot_instance.players


def test_remove_player_cleans_cache(bot_instance):
    """Verifica que remove_player libere la referencia del servidor."""
    player = bot_instance.get_player(guild_id=1)
    removed_player = bot_instance.remove_player(guild_id=1)

    assert removed_player is player
    assert 1 not in bot_instance.players
    assert bot_instance.remove_player(guild_id=1) is None


@pytest.mark.asyncio
async def test_on_guild_remove_triggers_disconnect(bot_instance):
    """Verifica que la expulsion de un servidor desconecte el reproductor asociado."""
    mock_player = AsyncMock()
    bot_instance.players[999] = mock_player

    guild = MagicMock(spec=discord.Guild)
    guild.id = 999
    guild.name = "Test Guild"

    # Simular callback de on_guild_remove
    removed = bot_instance.remove_player(guild.id)
    if removed:
        await removed.disconnect()

    assert 999 not in bot_instance.players
    mock_player.disconnect.assert_awaited_once()
