# 🎵 ChenchoBot

Bot musical para Discord desarrollado en Python con `discord.py`.

ChenchoBot está diseñado para reproducir música en canales de voz, utilizando información de Spotify para identificar las canciones y gestionar la reproducción mediante una cola.

## ✨ Características

Actualmente ChenchoBot cuenta con:

* 🎵 Reproducción de canciones
* 🔎 Búsqueda de canciones
* 🔗 Soporte para URLs de Spotify
* 📋 Soporte para playlists de Spotify
* ⏸️ Pausar reproducción
* ▶️ Reanudar reproducción
* ⏭️ Saltar canción
* ⏮️ Reproducir canción anterior
* 🔁 Modo repetición
* ⏹️ Detener reproducción
* 📜 Cola de reproducción
* 🎧 Gestión independiente del reproductor por servidor
* 🎤 Conexión automática a canales de voz

## 🛠️ Tecnologías

* Python 3.10+
* discord.py
* Spotify API
* FFmpeg
* yt-dlp
* Rich
* uv

## 📁 Estructura del proyecto

```text
ChenchoBot/
├── src/
│   ├── chencho_bot/
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── join.py
│   │   │   ├── leave.py
│   │   │   ├── music.py
│   │   │   ├── ping.py
│   │   │   └── search.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   ├── music/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── player.py
│   │   │   └── queue.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── audio.py
│   │   │   └── spotify.py
│   │   ├── utils/
│   │   │   ├── embeds.py
│   │   │   ├── logger.py
│   │   │   └── view.py
│   │   ├── __init__.py
│   │   └── main.py
│   └── __init__.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

> La estructura puede cambiar conforme avance el desarrollo del proyecto.

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Ker825/ChenchoBot.git
cd ChenchoBot
```

### 2. Instalar dependencias

El proyecto utiliza `uv` para gestionar el entorno y las dependencias.

```bash
uv sync
```

### 3. Configurar las variables de entorno

Copia `.env.example` como `.env`:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Después completa las variables necesarias dentro de `.env`.

### 4. Instalar FFmpeg

ChenchoBot utiliza FFmpeg para procesar el audio.

Comprueba que esté disponible:

```bash
ffmpeg -version
```

Si el comando no existe, instala FFmpeg y asegúrate de agregarlo al `PATH`.

## 🔐 Variables de entorno

El archivo `.env.example` contiene las variables necesarias para ejecutar el bot.

Ejemplo:

```env
DISCORD_TOKEN=your_discord_bot_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

**Nunca subas tu archivo `.env` a GitHub.**

El token del bot de Discord y las credenciales de Spotify son información privada.

## ▶️ Ejecutar el bot

Con `uv`:

```bash
uv run python -m chencho_bot
```

El comando exacto puede cambiar conforme avance la estructura del proyecto.

## 🎮 Comandos

| Comando     | Descripción                              |
| ----------- | ---------------------------------------- |
| `/ping`     | Comprueba que el bot está funcionando    |
| `/play`     | Reproduce o añade una canción a la cola  |
| `/pause`    | Pausa la reproducción                    |
| `/resume`   | Reanuda la reproducción                  |
| `/skip`     | Salta la canción actual                  |
| `/previous` | Reproduce la canción anterior            |
| `/loop`     | Activa o desactiva la repetición         |
| `/stop`     | Detiene la reproducción y limpia la cola |
| `/queue`    | Muestra la cola actual                   |

## 🚧 Estado del proyecto

ChenchoBot se encuentra actualmente en desarrollo.

Las funciones principales del reproductor musical están siendo implementadas progresivamente, con especial atención a:

* Gestión de cola
* Historial de reproducción
* Reproducción anterior
* Modo loop
* Manejo de errores
* Sincronización de reproducción
* Interacción con Discord
* Mejoras de arquitectura

## 📌 Próximos objetivos

* [ ] Mejorar la estabilidad del reproductor
* [ ] Completar el sistema de cola
* [ ] Mejorar el historial de reproducción
* [ ] Añadir controles mediante botones
* [ ] Añadir comandos de gestión de cola
* [ ] Mejorar los embeds
* [ ] Implementar reproducción continua
* [ ] Mejorar el manejo de errores
* [ ] Añadir más integración con Spotify
* [ ] Optimizar la arquitectura del bot

## 📄 Licencia

Este proyecto se encuentra actualmente en desarrollo. La licencia puede añadirse posteriormente.

````