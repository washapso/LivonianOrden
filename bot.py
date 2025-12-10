import discord
from discord.ext import commands
import os

# === ИМПОРТ МОДУЛЕЙ ===
from Modules.registration import setup_registration_commands
from Modules.organization import setup_organization_commands


TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Не установлена переменная окружения TOKEN")


# ================================
#     КЛАСС БОТА
# ================================

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Регистрируем команды из модулей
        await setup_registration_commands(self)
        await setup_organization_commands(self)

        # Синхронизация slash-команд
        try:
            synced = await self.tree.sync()
            print(f"🔄 Синхронизировано {len(synced)} слэш-команд.")
        except Exception as e:
            print(f"⚠ Ошибка синхронизации команд: {e}")


bot = MyBot()


# ================================
#        СОБЫТИЕ on_ready
# ================================

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"🤖 Бот {bot.user} запущен!")
    print(f"📊 Серверов: {len(bot.guilds)}")
    print(f"👤 ID: {bot.user.id}")
    print("=" * 50)


# ================================
#           ЗАПУСК
# ================================

bot.run(TOKEN)
