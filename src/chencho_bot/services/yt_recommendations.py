import asyncio
import logging
from typing import Any

from ytmusicapi import YTMusic

from chencho_bot.music.models import Track

logger = logging.getLogger(__name__)


class YouTubeMusicRecommender:
    """Proveedor de recomendaciones musicales consumiendo el algoritmo de radio de YouTube Music."""

    def __init__(self) -> None:
        self._ytmusic = YTMusic()

    async def get_recommendation(
        self,
        seed_track: Track,
        history: list[Track],
    ) -> Track | None:
        """Punto de entrada asincrono no bloqueante."""
        return await asyncio.to_thread(self._fetch_recommendation, seed_track, history)

    def _fetch_recommendation(
        self,
        seed_track: Track,
        history: list[Track],
    ) -> Track | None:
        try:
            # 1. Localizar la cancion semilla en YTMusic para extraer su videoId
            query = f"{seed_track.title} {seed_track.artist}"
            search_results = self._ytmusic.search(query=query, filter="songs", limit=1)

            if not search_results:
                logger.warning("No se encontro coincidencia en YTMusic para: %s", query)
                return None

            video_id = search_results[0].get("videoId")
            if not video_id:
                return None

            # 2. Consultar la estacion de radio asociada al tema
            radio = self._ytmusic.get_watch_playlist(videoId=video_id, limit=15)
            candidates: list[dict[str, Any]] = radio.get("tracks", [])

            # 3. Conjunto de exclusion: evitar repetir temas presentes en el historial
            excluded_titles = {t.title.casefold() for t in history}
            excluded_titles.add(seed_track.title.casefold())

            for item in candidates:
                title = item.get("title", "")
                if not title or title.casefold() in excluded_titles:
                    continue

                artists = ", ".join(a["name"] for a in item.get("artists", []))
                thumbnails = item.get("thumbnail", [])
                cover_url = thumbnails[-1]["url"] if thumbnails else None

                # Conversion de duracion (cadena MM:SS a ms)
                length_str = item.get("length", "0:00")
                duration_ms = self._parse_duration_to_ms(length_str)

                return Track(
                    title=title,
                    artist=artists,
                    album="YouTube Music Radio",
                    spotify_url=f"https://music.youtube.com/watch?v={item.get('videoId')}",
                    search_query=f"{title} {artists} audio",
                    cover_url=cover_url,
                    duration_ms=duration_ms,
                    requester=None,  # None indica cancion inyectada por Autoplay
                )

            return None

        except Exception as error:
            logger.error("Error al obtener recomendacion de YTMusic: %s", error)
            return None

    @staticmethod
    def _parse_duration_to_ms(length_str: str) -> int:
        parts = length_str.split(":")
        try:
            if len(parts) == 2:
                return (int(parts[0]) * 60 + int(parts[1])) * 1000
            if len(parts) == 3:
                return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        except ValueError:
            pass
        return 0
