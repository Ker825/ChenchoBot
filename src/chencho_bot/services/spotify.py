import logging
import re
from typing import Any, Final

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from chencho_bot.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Expresiones regulares universales para recursos de Spotify
RE_SPOTIFY_ID: Final[re.Pattern[str]] = re.compile(
    r"(?:https?:\/\/open\.spotify\.com\/(?:intl-[a-z]{2}\/)?|spotify:)"
    r"(track|playlist|album|artist)(?:[:/])([a-zA-Z0-9]+)"
)


def extract_spotify_resource(url_or_uri: str) -> tuple[str, str] | None:
    """Extrae la tupla (tipo_recurso, id_recurso) de una cadena de entrada sin invocar la API."""
    match = RE_SPOTIFY_ID.search(url_or_uri.strip())
    if match:
        return match.group(1), match.group(2)
    return None


def _format_track(
    data: dict[str, Any] | None,
    default_album: str | None = None,
    default_cover_url: str | None = None,
) -> dict[str, Any] | None:
    """Normaliza un payload de pista de Spotify al formato de diccionario de dominio."""
    if not data or not data.get("name"):
        return None

    artists = ", ".join(artist["name"] for artist in data.get("artists", []))
    album_data = data.get("album", {})
    images = album_data.get("images", [])

    cover_url = images[0]["url"] if images else default_cover_url
    album_name = album_data.get("name") or default_album or ""

    return {
        "title": data.get("name", "Desconocido"),
        "artist": artists,
        "album": album_name,
        "url": data.get("external_urls", {}).get("spotify", ""),
        "cover_url": cover_url,
        "duration_ms": data.get("duration_ms", 0),
    }


class SpotifyService:
    """Servicio para interactuar con la API de Spotify con resolucion de cliente perezosa."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: spotipy.Spotify | None = None,
    ) -> None:
        self._settings = settings
        self._client: spotipy.Spotify | None = client

    @property
    def client(self) -> spotipy.Spotify:
        """Instancia spotipy.Spotify de manera diferida solo cuando se realiza una peticion real."""
        if self._client is None:
            active_settings = self._settings or get_settings()

            if not active_settings.spotify_client_id or not active_settings.spotify_client_secret:
                raise RuntimeError(
                    "Credenciales de Spotify no configuradas. "
                    "Verifica SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en tu archivo .env."
                )

            # open_browser=False previene bloqueos en servidores o ejecuciones de test
            auth_manager = SpotifyOAuth(
                client_id=active_settings.spotify_client_id,
                client_secret=active_settings.spotify_client_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="playlist-read-private playlist-read-collaborative",
                open_browser=False,
            )
            self._client = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Cliente de Spotify autenticado e inicializado bajo demanda.")

        return self._client

    def search_track(self, query: str) -> dict[str, Any] | None:
        """Busca una pista musical por texto."""
        try:
            results = self.client.search(q=query, limit=1, type="track")
            items = results.get("tracks", {}).get("items", []) if results else []
            if not items:
                return None
            return _format_track(items[0])
        except Exception as error:
            logger.error("Error en busqueda textual de Spotify ('%s'): %s", query, error)
            return None

    def get_track_by_url(self, url_or_id: str) -> dict[str, Any] | None:
        """Obtiene una pista mediante su URL o identificador unico."""
        resource = extract_spotify_resource(url_or_id)
        track_id = resource[1] if resource and resource[0] == "track" else url_or_id

        try:
            data = self.client.track(track_id)
            return _format_track(data)
        except Exception as error:
            logger.error("Error al obtener track por identificador '%s': %s", url_or_id, error)
            return None

    def get_album_tracks(self, url_or_id: str) -> list[dict[str, Any]]:
        """Obtiene todas las pistas de un album paginando en lotes de 50."""
        resource = extract_spotify_resource(url_or_id)
        album_id = resource[1] if resource and resource[0] == "album" else url_or_id

        tracks: list[dict[str, Any]] = []
        try:
            album_data = self.client.album(album_id)
            album_name = album_data.get("name", "Desconocido")
            images = album_data.get("images", [])
            cover_url = images[0]["url"] if images else None

            offset = 0
            limit = 50

            while True:
                batch = self.client.album_tracks(album_id, limit=limit, offset=offset)
                items = batch.get("items", [])
                if not items:
                    break

                for item in items:
                    formatted = _format_track(
                        item,
                        default_album=album_name,
                        default_cover_url=cover_url,
                    )
                    if formatted:
                        tracks.append(formatted)

                offset += len(items)
                if batch.get("next") is None:
                    break

            return tracks
        except Exception as error:
            logger.error("Error al obtener pistas del album '%s': %s", url_or_id, error)
            return []

    def get_artist_top_tracks(
        self,
        url_or_id: str,
        country: str = "MX",
    ) -> list[dict[str, Any]]:
        """Obtiene las canciones mas populares de un artista con fallback resiliente ante errores 403."""
        resource = extract_spotify_resource(url_or_id)
        artist_id = resource[1] if resource and resource[0] == "artist" else url_or_id

        tracks: list[dict[str, Any]] = []

        # 1. Intento primario mediante endpoint de top-tracks
        try:
            results = self.client.artist_top_tracks(artist_id, country=country)
            for item in results.get("tracks", []):
                formatted = _format_track(item)
                if formatted:
                    tracks.append(formatted)

            if tracks:
                return tracks
        except Exception as error:
            logger.warning(
                "Endpoint artist_top_tracks bloqueado o no disponible (%s). Activando fallback por busqueda.",
                error,
            )

        # 2. Fallback: buscar canciones relevantes por catalogo del artista
        try:
            artist_info = self.client.artist(artist_id)
            artist_name = artist_info.get("name")
            if not artist_name:
                return []

            search_query = f'artist:"{artist_name}"'
            search_results = self.client.search(
                q=search_query,
                type="track",
                limit=10,
                market=country,
            )

            items = search_results.get("tracks", {}).get("items", []) if search_results else []
            for item in items:
                formatted = _format_track(item)
                if formatted:
                    tracks.append(formatted)

            logger.info(
                "Recuperadas %d canciones para el artista '%s' mediante fallback de busqueda.",
                len(tracks),
                artist_name,
            )
            return tracks
        except Exception as fallback_error:
            logger.error(
                "Error critico al ejecutar fallback para el artista '%s': %s",
                artist_id,
                fallback_error,
            )
            return []

    def get_playlist_tracks(self, url_or_id: str) -> list[dict[str, Any]]:
        """Obtiene todas las canciones de una playlist de Spotify paginando por lotes."""
        resource = extract_spotify_resource(url_or_id)
        playlist_id = resource[1] if resource and resource[0] == "playlist" else url_or_id

        tracks: list[dict[str, Any]] = []
        offset = 0
        limit = 100

        try:
            while True:
                results = self.client.playlist_items(
                    playlist_id,
                    offset=offset,
                    limit=limit,
                    additional_types=("track",),
                )
                items = results.get("items", [])
                if not items:
                    break

                for item in items:
                    track_data = item.get("item") or item.get("track")
                    formatted = _format_track(track_data)
                    if formatted:
                        tracks.append(formatted)

                offset += len(items)
                if results.get("next") is None:
                    break

            return tracks
        except Exception as error:
            logger.error("Error al obtener pistas de playlist '%s': %s", url_or_id, error)
            return []


# ---------------------------------------------------------------------------
# Instancia compartida perezosa y funciones de compatibilidad
# ---------------------------------------------------------------------------

_default_service: SpotifyService | None = None


def get_spotify_service() -> SpotifyService:
    """Obtiene la instancia compartida de SpotifyService."""
    global _default_service
    if _default_service is None:
        _default_service = SpotifyService()
    return _default_service


def search_track(query: str) -> dict[str, Any] | None:
    return get_spotify_service().search_track(query)


def get_track_by_url(url_or_id: str) -> dict[str, Any] | None:
    return get_spotify_service().get_track_by_url(url_or_id)


def get_album_tracks(url_or_id: str) -> list[dict[str, Any]]:
    return get_spotify_service().get_album_tracks(url_or_id)


def get_artist_top_tracks(url_or_id: str, country: str = "MX") -> list[dict[str, Any]]:
    return get_spotify_service().get_artist_top_tracks(url_or_id, country)


def get_playlist_tracks(url_or_id: str) -> list[dict[str, Any]]:
    return get_spotify_service().get_playlist_tracks(url_or_id)
