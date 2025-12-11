import os
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN")  # БЕРЁМ ТОКЕН ИМЕННО ИЗ СЕКРЕТА

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Бот вошёл как {bot.user} и работает на Zeabur!")

bot.run(TOKEN)
