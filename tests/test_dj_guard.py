from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from chencho_bot.database.models import GuildConfig
from chencho_bot.utils.guards import DJGuard


@pytest.fixture
def mock_interaction():
    """Genera una interaccion base simulada de Discord."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 5555

    member = MagicMock(spec=discord.Member)
    member.guild_permissions = MagicMock()
    member.guild_permissions.administrator = False
    member.roles = []
    interaction.user = member

    # Simular estado de canal de voz con multiples humanos
    voice_channel = MagicMock()
    other_member = MagicMock(spec=discord.Member)
    other_member.bot = False
    member.bot = False
    voice_channel.members = [member, other_member]

    voice_client = MagicMock(spec=discord.VoiceClient)
    voice_client.channel = voice_channel
    interaction.guild.voice_client = voice_client

    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    return interaction


@pytest.mark.asyncio
async def test_dj_guard_admin_bypass(mock_interaction, monkeypatch):
    """Un administrador debe ser aprobado sin consultar la base de datos."""
    monkeypatch.setattr(
        "chencho_bot.utils.guards.VoiceGuard.ensure_same_channel",
        AsyncMock(return_value=True),
    )
    mock_interaction.user.guild_permissions.administrator = True
    config_service = AsyncMock()

    allowed = await DJGuard.can_control(mock_interaction, config_service)

    assert allowed is True
    config_service.get_config.assert_not_called()


@pytest.mark.asyncio
async def test_dj_guard_solo_human_bypass(mock_interaction, monkeypatch):
    """Si el usuario es el unico humano presente en el canal, se autoriza."""
    monkeypatch.setattr(
        "chencho_bot.utils.guards.VoiceGuard.ensure_same_channel",
        AsyncMock(return_value=True),
    )
    # Dejar solo al solicitante y un bot
    bot_member = MagicMock()
    bot_member.bot = True
    mock_interaction.guild.voice_client.channel.members = [mock_interaction.user, bot_member]

    config_service = AsyncMock()

    allowed = await DJGuard.can_control(mock_interaction, config_service)

    assert allowed is True
    config_service.get_config.assert_not_called()


@pytest.mark.asyncio
async def test_dj_guard_free_mode(mock_interaction, monkeypatch):
    """Si dj_role_id es None, el comando opera en modo libre."""
    monkeypatch.setattr(
        "chencho_bot.utils.guards.VoiceGuard.ensure_same_channel",
        AsyncMock(return_value=True),
    )
    config_service = AsyncMock()
    config_service.get_config.return_value = GuildConfig(guild_id=5555, dj_role_id=None)

    allowed = await DJGuard.can_control(mock_interaction, config_service)

    assert allowed is True


@pytest.mark.asyncio
async def test_dj_guard_denies_missing_role(mock_interaction, monkeypatch):
    """Deniega la accion y envia mensaje si el usuario carece del rol configurado."""
    monkeypatch.setattr(
        "chencho_bot.utils.guards.VoiceGuard.ensure_same_channel",
        AsyncMock(return_value=True),
    )
    config_service = AsyncMock()
    config_service.get_config.return_value = GuildConfig(guild_id=5555, dj_role_id=777)

    # El usuario no posee el rol 777
    role_other = MagicMock()
    role_other.id = 111
    mock_interaction.user.roles = [role_other]

    allowed = await DJGuard.can_control(mock_interaction, config_service)

    assert allowed is False
    mock_interaction.response.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_dj_guard_allows_matching_role(mock_interaction, monkeypatch):
    """Autoriza la accion si el usuario tiene el rol DJ requerido."""
    monkeypatch.setattr(
        "chencho_bot.utils.guards.VoiceGuard.ensure_same_channel",
        AsyncMock(return_value=True),
    )
    config_service = AsyncMock()
    config_service.get_config.return_value = GuildConfig(guild_id=5555, dj_role_id=777)

    role_dj = MagicMock()
    role_dj.id = 777
    mock_interaction.user.roles = [role_dj]

    allowed = await DJGuard.can_control(mock_interaction, config_service)

    assert allowed is True
