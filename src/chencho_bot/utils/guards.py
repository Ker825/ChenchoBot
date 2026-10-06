import discord

from chencho_bot.services.guild_config import GuildConfigService


class VoiceGuard:
    """Validador defensivo de presencia y autoridad en canales de voz."""

    @staticmethod
    async def validate_voice_connection(
        interaction: discord.Interaction,
    ) -> tuple[discord.Member, discord.VoiceState] | None:
        """Comprueba que la interaccion provenga de un miembro en un canal de voz."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.followup.send(
                "Este comando solo puede ejecutarse dentro de un servidor.",
                ephemeral=True,
            )
            return None

        voice_state = interaction.user.voice
        if not voice_state or not voice_state.channel:
            await interaction.followup.send(
                "Debes estar conectado a un canal de voz.",
                ephemeral=True,
            )
            return None

        return interaction.user, voice_state

    @classmethod
    async def ensure_same_channel(cls, interaction: discord.Interaction) -> bool:
        """Verifica que el usuario comparta el mismo canal de voz con el bot."""
        validation = await cls.validate_voice_connection(interaction)
        if not validation:
            return False

        _, user_voice = validation
        bot_voice = interaction.guild.voice_client if interaction.guild else None

        if bot_voice and bot_voice.channel != user_voice.channel:
            await interaction.followup.send(
                "Debes estar en el mismo canal de voz que el bot para controlar la reproduccion.",
                ephemeral=True,
            )
            return False

        return True


class DJGuard:
    """Valida si un usuario tiene permisos para controlar la reproducción."""

    @classmethod
    async def can_control(
        cls,
        interaction: discord.Interaction,
        config_service: GuildConfigService,
    ) -> bool:
        """Determina si un usuario tiene permisos suficientes para controlar el flujo de audio."""
        if not await VoiceGuard.ensure_same_channel(interaction):
            return False

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False

        # 1. Privilegios de administrador (acceso irrestricto)
        if interaction.user.guild_permissions.administrator:
            return True

        # 2. Regla de soledad: unico humano presente en el canal de voz
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.channel:
            human_members = [m for m in voice_client.channel.members if not m.bot]
            if len(human_members) <= 1:
                return True

        # 3. Validacion contra rol DJ configurado en base de datos
        config = await config_service.get_config(interaction.guild.id)
        if config.dj_role_id is None:
            return True

        has_dj_role = any(role.id == config.dj_role_id for role in interaction.user.roles)
        if has_dj_role:
            return True

        # Denegacion con mensaje efimero
        message = (
            f"Accion denegada. Se requiere el rol <@&{config.dj_role_id}> "
            "o permisos de administrador para ejecutar este comando."
        )
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

        return False

    @staticmethod
    async def ensure_permission(interaction: discord.Interaction) -> bool:
        """Comprueba si el usuario puede ejecutar una acción de DJ."""

        # 1. Debe estar en el mismo canal de voz que el bot.
        if not await VoiceGuard.ensure_same_channel(interaction):
            return False

        user = interaction.user
        guild = interaction.guild

        if guild is None:
            return False

        # 2. Los administradores tienen acceso total.
        if user.guild_permissions.administrator:
            return True

        # Obtener el canal de voz del bot.
        bot = interaction.client

        if not isinstance(bot, discord.Client):
            return False

        bot_channel = None

        for voice_client in bot.voice_clients:
            if voice_client.guild.id == guild.id:
                bot_channel = voice_client.channel
                break

        if bot_channel is None:
            return False

        # 3. Si el solicitante es el único humano del canal,
        #    obtiene permiso automáticamente.
        human_members = [member for member in bot_channel.members if not member.bot]

        if len(human_members) == 1 and human_members[0].id == user.id:
            return True

        # 4. Obtener configuración del servidor.
        config_service = GuildConfigService()
        config = await config_service.get_config(guild.id)

        # Sin rol DJ configurado -> servidor en modo libre.
        if config.dj_role_id is None:
            return True

        # Verificar si el usuario tiene el rol DJ.
        if any(role.id == config.dj_role_id for role in user.roles):
            return True

        # Sin permisos.
        await interaction.response.send_message(
            "No tienes permisos para controlar la reproducción.",
            ephemeral=True,
        )

        return False
