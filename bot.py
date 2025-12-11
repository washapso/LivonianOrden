import os
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = "ТОКЕН_БОТА"
GUILD_ID = 123456789012345678  # ID твоего сервера

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# === Создаём клиента и дерево команд ===
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=None
        )

    async def setup_hook(self):
        # Загрузка всех модулей
        for file in os.listdir("./modules"):
            if file.endswith(".py"):
                await self.load_extension(f"modules.{file[:-3]}")
                print(f"📦 Загружен модуль: {file}")

        # Синхронизация команд с сервером
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Слэш-команды синхронизированы!")

bot = MyBot()

# === Событие запуска ===
@bot.event
async def on_ready():
    print(f"🤖 Бот запущен как {bot.user}")

# === Запуск ===
bot.run(TOKEN)
