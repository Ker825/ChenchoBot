import asyncio
from typing import Any

import yt_dlp

YTDL_OPTIONS: dict[str, Any] = {
    # Prioriza solo audio. Si no hay, usa el mejor formato disponible.
    "format": "bestaudio[ext=m4a]/bestaudio/best[height<=480]/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    # Permite buscar directamente en YouTube cuando recibe texto.
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    # Configuración del reproductor de YouTube.
    "extractor_args": {
        "youtube": {
            # Clientes utilizados para reducir problemas de extracción.
            "player_client": ["android", "mweb"],
        }
    },
}


ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


def _extract_sync(query: str) -> dict[str, Any] | None:
    """
    Extrae la información del audio de forma síncrona.

    Esta función NO debe ejecutarse directamente desde el event loop.
    """

    try:
        data = ytdl.extract_info(
            query,
            download=False,
        )

        if not data:
            return None

        # Cuando yt-dlp realiza una búsqueda, devuelve "entries".
        if "entries" in data:
            entries = data.get("entries")

            if not entries:
                return None

            data = entries[0]

        return {
            "url": data.get("url"),
            "title": data.get(
                "title",
                "Audio desconocido",
            ),
            "duration": data.get(
                "duration",
                0,
            ),
            "webpage_url": data.get(
                "webpage_url",
                "",
            ),
        }

    except Exception as e:
        print(f"Error extrayendo audio: {e}")
        return None


async def get_audio_stream(
    query: str,
) -> dict[str, Any] | None:
    """
    Ejecuta yt-dlp en un hilo secundario.

    Esto evita bloquear el event loop de Discord mientras
    yt-dlp obtiene la información del audio.
    """

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        None,
        _extract_sync,
        query,
    )
