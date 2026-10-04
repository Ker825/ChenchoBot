from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from chencho_bot.commands.music import Music


@pytest.fixture
def music_cog():
    bot = MagicMock()
    return Music(bot=bot)


@pytest.mark.asyncio
async def test_authority_check_fails_when_user_in_different_voice_channel(music_cog):
    """Verifica que un usuario en otro canal de voz no pueda controlar la reproduccion."""
    interaction = AsyncMock(spec=discord.Interaction)
    member = MagicMock(spec=discord.Member)
    bot_voice = MagicMock(spec=discord.VoiceClient)

    # Configurar canales distintos
    channel_user = MagicMock()
    channel_bot = MagicMock()
    member.voice = MagicMock(channel=channel_user)
    bot_voice.channel = channel_bot

    interaction.guild = MagicMock(voice_client=bot_voice)
    interaction.user = member

    authorized = await music_cog._check_playback_channel_authority(interaction)

    assert authorized is False
    interaction.followup.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_command_disables_active_view(music_cog):
    """Verifica que /stop inhabilite la vista en el handler de UI."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.guild = MagicMock(id=123)

    mock_player = MagicMock()
    mock_handler = AsyncMock()

    music_cog.get_player = MagicMock(return_value=mock_player)
    music_cog.ui_handlers[123] = mock_handler
    music_cog._check_playback_channel_authority = AsyncMock(return_value=True)

    await music_cog.stop.callback(music_cog, interaction)

    mock_player.stop.assert_called_once()
    mock_handler.disable_current_view.assert_awaited_once()
