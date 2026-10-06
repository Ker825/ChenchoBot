import asyncio

from chencho_bot.database.models import Base
from chencho_bot.database.repositories.guild_repository import GuildRepository
from chencho_bot.database.session import async_session_factory, engine


async def smoke_test() -> None:
    print("[1/3] Probando conexion y creando esquemas DDL...")
    async with engine.begin() as conn:
        # Crea las tablas si no existen en la BD chenchobot
        await conn.run_sync(Base.metadata.create_all)
    print("Tablas creadas correctamente.")

    print("[2/3] Probando transaccion de escritura (Upsert)...")
    test_guild_id = 123456789012345678  # Snowflake de 64 bits para validar BigInteger

    async with async_session_factory() as session:
        repo = GuildRepository(session)
        # get_or_create ejecuta ON CONFLICT DO NOTHING
        config = await repo.get_or_create(guild_id=test_guild_id)
        await session.commit()
        print(f"Registro persistido: Guild ID = {config.guild_id}, Volumen = {config.default_volume}")

    print("[3/3] Probando lectura desde una nueva sesion...")
    async with async_session_factory() as session:
        repo = GuildRepository(session)
        persisted = await repo.get(guild_id=test_guild_id)
        assert persisted is not None
        print(f"Lectura verificada: Autoplay = {persisted.autoplay_enabled}")

    # Cierre limpio del pool de conexiones
    await engine.dispose()
    print("Prueba completada con exito. La base de datos esta lista.")


if __name__ == "__main__":
    asyncio.run(smoke_test())
