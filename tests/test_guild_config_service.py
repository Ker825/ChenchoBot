from unittest.mock import AsyncMock, MagicMock

import pytest

from chencho_bot.database.models import GuildConfig
from chencho_bot.services.guild_config import GuildConfigService


@pytest.fixture
def mock_session_factory():
    """Genera una factoria de sesiones asincrona simulada."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None
    return mock_factory, mock_session


@pytest.mark.asyncio
async def test_get_config_cache_miss_then_hit(mock_session_factory, monkeypatch):
    """Verifica que tras un cache miss se guarde en memoria y no se vuelva a consultar la BD."""
    factory, session = mock_session_factory
    service = GuildConfigService(session_factory=factory)

    fake_config = GuildConfig(
        guild_id=123,
        dj_role_id=None,
        default_volume=100,
        autoplay_enabled=False,
        inactivity_timeout_seconds=180,
    )

    mock_repo = AsyncMock()
    mock_repo.get_or_create.return_value = fake_config
    monkeypatch.setattr(
        "chencho_bot.services.guild_config.GuildRepository",
        lambda s: mock_repo,
    )

    # 1. Primera consulta: Cache Miss (debe consultar repositorio y confirmar transaccion)
    config_1 = await service.get_config(123)
    assert config_1 == fake_config
    mock_repo.get_or_create.assert_awaited_once_with(123)
    session.commit.assert_awaited_once()

    # 2. Segunda consulta: Cache Hit (debe resolverse desde self._cache)
    config_2 = await service.get_config(123)
    assert config_2 == fake_config
    assert mock_repo.get_or_create.await_count == 1


@pytest.mark.asyncio
async def test_set_dj_role_updates_db_and_cache(mock_session_factory, monkeypatch):
    """Comprueba que una actualizacion persista en BD y sincronice la cache local."""
    factory, session = mock_session_factory
    service = GuildConfigService(session_factory=factory)

    updated_config = GuildConfig(
        guild_id=123,
        dj_role_id=999,
        default_volume=100,
    )

    mock_repo = AsyncMock()
    mock_repo.set_dj_role.return_value = updated_config
    monkeypatch.setattr(
        "chencho_bot.services.guild_config.GuildRepository",
        lambda s: mock_repo,
    )

    result = await service.set_dj_role(guild_id=123, role_id=999)

    assert result == updated_config
    mock_repo.set_dj_role.assert_awaited_once_with(123, 999)
    session.commit.assert_awaited_once()

    # Verificar que la cache contiene la nueva instancia
    cached = await service.get_config(123)
    assert cached.dj_role_id == 999


@pytest.mark.asyncio
async def test_invalidate_clears_cache_entry(mock_session_factory):
    """Verifica que invalidar fuerce una posterior consulta a BD."""
    factory, _ = mock_session_factory
    service = GuildConfigService(session_factory=factory)

    service._cache[123] = GuildConfig(guild_id=123)
    assert 123 in service._cache

    service.invalidate(123)
    assert 123 not in service._cache
