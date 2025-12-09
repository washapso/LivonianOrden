import discord
from discord import app_commands
from discord.ext import commands
import asyncio

# ⚠️ ВАЖНО: Замените на НОВЫЙ токен из Discord Developer Portal!
TOKEN = "MTQ0ODA4MTEwODAwNzkxNTUzMQ.GhSXtX.hMdxTeyNkKHSvhXbASXJQMlGg-HKh6xU8bNSlA"

# --- НАСТРОЙКИ ---
WHITELIST_ROLES = [
    1448012916115898560  # ID ролей с доступом к каналам
]

MESSAGE_CHANNEL_ID = 1448079215219183779


# --- КЛАСС БОТА ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )

    async def setup_hook(self):
        # Регистрируем persistent view
        self.add_view(CreateChannelButton())
        
        await self.tree.sync()
        print("✅ Slash-команды синхронизированы.")
        print("✅ Persistent view зарегистрирован.")


bot = MyBot()


# ============================================
#   КНОПКА ДЛЯ СОЗДАНИЯ ПРИВАТНОГО КАНАЛА
# ============================================

class CreateChannelButton(discord.ui.View):
    def __init__(self):
        # timeout=None делает view постоянным
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать канал", 
        style=discord.ButtonStyle.green,
        custom_id="create_channel_button"  # Важно для persistent view!
    )
    async def create_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Название канала
        channel_name = f"регистрация-предприятия-{user.name}".lower().replace(" ", "-")

        # Проверка: нет ли уже канала с таким названием
        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            await interaction.response.send_message(
                "❗ У вас уже есть активный канал для регистрации.",
                ephemeral=True
            )
            return

        # Права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),

            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True
            )
        }

        # Добавление ролей из whitelist
        for role_id in WHITELIST_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        try:
            # Создание канала
            new_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Регистрация предприятия для {user.name}"
            )

            await interaction.response.send_message(
                f"✅ Канал создан: {new_channel.mention}",
                ephemeral=True
            )

            # Приветственное сообщение
            embed = discord.Embed(
                title="Добро пожаловать!",
                description=f"{user.mention}, опишите своё предприятие в этом канале.",
                color=0x2ecc71
            )
            await new_channel.send(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ У бота нет прав на создание каналов!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )


# ============================================
#   КОМАНДА ДЛЯ ОТПРАВКИ СООБЩЕНИЯ С КНОПКОЙ
# ============================================

@bot.tree.command(name="setup_registration", description="Отправить кнопку для создания приватных каналов")
@app_commands.checks.has_permissions(administrator=True)
async def setup_registration(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(MESSAGE_CHANNEL_ID)
    
    if not channel:
        return await interaction.response.send_message(
            "❌ Канал не найден! Проверьте MESSAGE_CHANNEL_ID.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="🏢 Регистрация предприятий",
        description="Нажмите кнопку ниже, чтобы создать приватный канал для регистрации вашего предприятия.",
        color=0x2ecc71
    )

    await channel.send(embed=embed, view=CreateChannelButton())
    await interaction.response.send_message("✅ Сообщение отправлено!", ephemeral=True)


# ============================================
#   КОМАНДА ДЛЯ УДАЛЕНИЯ КАНАЛА
# ============================================

@bot.command(name="удалить")
async def delete_channel(ctx):
    # Проверка: название канала начинается с "регистрация-предприятия-"
    if not ctx.channel.name.startswith("регистрация-предприятия-"):
        await ctx.send("❌ Эта команда работает только в каналах регистрации предприятий!")
        return
    
    # Проверка: пользователь является владельцем канала
    # Ищем имя пользователя в названии канала
    channel_owner_name = ctx.channel.name.replace("регистрация-предприятия-", "").replace("-", " ")
    
    # Сравниваем с именем пользователя (или проверяем права доступа)
    is_owner = False
    
    # Проверка 1: Имя пользователя в названии канала
    if ctx.author.name.lower().replace(" ", "-") in ctx.channel.name:
        is_owner = True
    
    # Проверка 2: У пользователя есть права на отправку сообщений (значит это его канал)
    overwrites = ctx.channel.overwrites_for(ctx.author)
    if overwrites.send_messages is True:
        # Проверяем что это не просто роль из whitelist
        if ctx.author not in [member for role_id in WHITELIST_ROLES for member in ctx.guild.get_role(role_id).members if ctx.guild.get_role(role_id)]:
            is_owner = True
        else:
            # Дополнительная проверка: если пользователь в whitelist, но канал создан для него
            if ctx.author.name.lower().replace(" ", "-") in ctx.channel.name:
                is_owner = True
    
    if not is_owner:
        await ctx.send("❌ Только создатель канала может его удалить!")
        return
    
    # Подтверждение удаления
    embed = discord.Embed(
        title="⚠️ Подтверждение удаления",
        description=f"Вы уверены, что хотите удалить канал {ctx.channel.mention}?\n\nНажмите ✅ для подтверждения или ❌ для отмены.\n\n**Канал будет удален через 10 секунд после подтверждения.**",
        color=0xe74c3c
    )
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        if str(reaction.emoji) == "✅":
            await ctx.send("✅ Канал будет удален через 10 секунд...")
            await asyncio.sleep(10)
            await ctx.channel.delete(reason=f"Удалено пользователем {ctx.author.name}")
        else:
            await ctx.send("❌ Удаление отменено.")
    
    except asyncio.TimeoutError:
        await ctx.send("⏱️ Время вышло. Удаление отменено.")


# ============================================
#   СОБЫТИЯ БОТА
# ============================================

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    print(f"📊 Серверов: {len(bot.guilds)}")


# ============================================
bot.run(TOKEN)