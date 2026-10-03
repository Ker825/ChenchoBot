import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Obtener el token de Discord
TOKEN = os.getenv("DISCORD_API_TOKEN")


# Permisos que tendrá el bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="/",
    intents=intents,
)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")


@bot.command()
async def hola(ctx):
    await ctx.send("¡Hola! ¿Cómo estás?")


# Iniciar el bot
bot.run(str(TOKEN))
