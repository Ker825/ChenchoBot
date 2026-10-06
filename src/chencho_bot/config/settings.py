import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class InvalidCookieFileError(Exception):
    """Excepción lanzada cuando el archivo cookies.txt no cumple el estándar Netscape."""

    pass


class ConfigurationError(Exception):
    """Excepción lanzada cuando faltan parámetros requeridos para el entorno de producción."""

    pass


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


def validate_netscape_cookies(file_path: Path) -> None:
    """Valida que el archivo exista y cumpla con el formato Netscape HTTP Cookie File."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Archivo de cookies no encontrado: {file_path}")

    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise InvalidCookieFileError(f"El archivo {file_path.name} está vacío.")

    first_line = lines[0]
    valid_headers = ("# Netscape HTTP Cookie File", "# HTTP Cookie File")
    if not any(first_line.startswith(header) for header in valid_headers):
        raise InvalidCookieFileError(
            f"Encabezado inválido en {file_path.name}. Debe iniciar con '# Netscape HTTP Cookie File'."
        )

    cookie_entries_count = 0
    for line_idx, line in enumerate(lines[1:], start=2):
        if line.startswith("#"):
            continue

        columns = line.split("\t")
        if len(columns) != 7:
            raise InvalidCookieFileError(
                f"Línea {line_idx} mal formada en {file_path.name}: "
                f"se esperaban 7 campos separados por tabuladores (\\t), se obtuvieron {len(columns)}."
            )

        cookie_entries_count += 1

    if cookie_entries_count == 0:
        raise InvalidCookieFileError(
            f"El archivo {file_path.name} tiene la cabecera correcta pero no contiene cookies válidas."
        )


@dataclass(frozen=True)
class Settings:
    """Esquema desacoplado de configuración sin efectos secundarios al importar."""

    discord_token: str
    spotify_client_id: str
    spotify_client_secret: str
    test_guild_id: str | None
    cookies_path: Path
    database_url: str
    base_dir: Path

    def validate_production(self) -> None:
        """Valida explícitamente tokens y archivos para el arranque en producción."""
        missing: list[str] = []
        if not self.discord_token:
            missing.append("DISCORD_TOKEN")
        if not self.spotify_client_id:
            missing.append("SPOTIFY_CLIENT_ID")
        if not self.spotify_client_secret:
            missing.append("SPOTIFY_CLIENT_SECRET")
        if not self.database_url:
            missing.append("DATABASE_URL")

        if missing:
            raise ConfigurationError(
                f"Faltan variables de entorno obligatorias: {', '.join(missing)}. Verifica tu archivo .env"
            )

        if not self.cookies_path.is_file():
            raise FileNotFoundError(
                f"Archivo de cookies no encontrado o no es un archivo regular en: {self.cookies_path}"
            )

        # Valida que el archivo cumpla el estándar Netscape
        validate_netscape_cookies(self.cookies_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Fábrica de configuración cacheada que no lanza errores durante la importación."""
    cookies_env = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
    raw_cookies_path = Path(cookies_env).expanduser()

    if raw_cookies_path.is_absolute():
        resolved_cookies = raw_cookies_path.resolve()
    else:
        resolved_cookies = (BASE_DIR / raw_cookies_path).resolve()

    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        test_guild_id=os.getenv("TEST_GUILD_ID"),
        database_url=os.getenv("DATABASE_URL"),
        cookies_path=resolved_cookies,
        base_dir=BASE_DIR,
    )


# Compatibilidad hacia atrás para módulos que importan constantes directamente
_active_settings = get_settings()
DISCORD_TOKEN = _active_settings.discord_token
SPOTIFY_CLIENT_ID = _active_settings.spotify_client_id
SPOTIFY_CLIENT_SECRET = _active_settings.spotify_client_secret
TEST_GUILD_ID = _active_settings.test_guild_id
DATABASE_URL = _active_settings.database_url
COOKIES_PATH = _active_settings.cookies_path
