import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class InvalidCookieFileError(Exception):
    """Excepción lanzada cuando el archivo cookies.txt no cumple el estándar Netscape."""  # noqa: E501

    pass


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Resolver cookies.txt soportando rutas relativas a la raíz o absolutas
_cookies_env = os.getenv("YOUTUBE_COOKIES_PATH", "cookies.txt")
_raw_cookies_path = Path(_cookies_env).expanduser()

if _raw_cookies_path.is_absolute():
    COOKIES_PATH = _raw_cookies_path.resolve()
else:
    COOKIES_PATH = (BASE_DIR / _raw_cookies_path).resolve()

# Validaciones de variables obligatorias
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN no encontrado. Verifica tu archivo .env")

if not SPOTIFY_CLIENT_ID:
    raise ValueError("SPOTIFY_CLIENT_ID no encontrado. Verifica tu archivo .env")

if not SPOTIFY_CLIENT_SECRET:
    raise ValueError("SPOTIFY_CLIENT_SECRET no encontrado. Verifica tu archivo .env")

# Validar existencia y que sea un archivo regular
if not COOKIES_PATH.is_file():
    raise FileNotFoundError(
        f"Archivo de cookies no encontrado o no es un archivo regular en: {COOKIES_PATH}"  # noqa: E501
    )


def validate_netscape_cookies(file_path: Path) -> None:
    """
    Valida que el archivo exista y cumpla con el formato Netscape HTTP Cookie File.
    Lanza FileNotFoundError o InvalidCookieFileError si no es válido.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Archivo de cookies no encontrado: {file_path}")

    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise InvalidCookieFileError(f"El archivo {file_path.name} está vacío.")

    # 1. Validar la cabecera estándar
    first_line = lines[0]
    valid_headers = ("# Netscape HTTP Cookie File", "# HTTP Cookie File")
    if not any(first_line.startswith(header) for header in valid_headers):
        raise InvalidCookieFileError(
            f"Encabezado inválido en {file_path.name}. "
            "Debe iniciar con '# Netscape HTTP Cookie File'."
        )

    # 2. Validar que existan registros de cookies y que tengan 7 columnas delimitadas por tabulador # noqa: E501
    cookie_entries_count = 0
    for line_idx, line in enumerate(lines[1:], start=2):
        if line.startswith("#"):
            continue  # Ignorar comentarios intermedios

        columns = line.split("\t")
        if len(columns) != 7:
            raise InvalidCookieFileError(
                f"Línea {line_idx} mal formada en {file_path.name}: "
                f"se esperaban 7 campos separados por tabuladores (\\t), se obtuvieron {len(columns)}."  # noqa: E501
            )

        cookie_entries_count += 1

    if cookie_entries_count == 0:
        raise InvalidCookieFileError(
            f"El archivo {file_path.name} tiene la cabecera correcta pero no contiene cookies válidas."  # noqa: E501
        )
