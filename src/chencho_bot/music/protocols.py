from typing import Protocol

from chencho_bot.music.models import Track


class RecommendationProvider(Protocol):
    """Contrato abstracto para proveedores de recomendaciones musicales."""

    async def get_next_recommendation(
        self,
        seed_track: Track,
        history: list[Track],
    ) -> Track | None:
        """Obtiene la siguiente pista recomendada evitando las que esten en el historial."""
        ...
