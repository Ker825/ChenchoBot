import discord


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
