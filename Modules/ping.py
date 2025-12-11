from discord.ext import commands
import discord
from discord import app_commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Проверка ответа бота")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Понг!")

async def setup(bot):
    await bot.add_cog(Ping(bot))
