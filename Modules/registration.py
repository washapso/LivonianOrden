import discord
from discord import app_commands
from discord.ext import commands
import datetime

# ==============================
# НАСТРОЙКИ
# ==============================

MESSAGE_CHANNEL_ID = 1448079215219183779
REGISTRATION_CATEGORY_ID = 1448103698755485870

WHITELIST_ROLES = [
    1448012916115898560
]


# ==============================
# VIEW: КНОПКА СОЗДАТЬ КАНАЛ
# ==============================

class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(
        label="Создать канал",
        style=discord.ButtonStyle.green,
        custom_id="registration_create_channel"
    )
    async def create_channel(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user

        # Формат названия канала
        channel_name = f"регистрация-предприятия-{user.name}".lower().replace(" ", "-")

        # Проверка существующего канала
        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            return await interaction.response.send_message(
                "❌ У вас уже есть канал регистрации!",
                ephemeral=True
            )

        # Создаем права
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
                manage_channels=True,
                read_message_history=True
            )
        }

        # Роли проверяющих
        for role_id in WHITELIST_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        # Категория
        category = guild.get_channel(REGISTRATION_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            category = None

        # Создаем канал
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Регистрация предприятия: {user}"
        )

        # -----------------------
        # 1️⃣ EMBED сообщение
        # -----------------------

        embed = discord.Embed(
            title="📄 Регистрация предприятия",
            description=(
                "Опишите подробно, чем занимается ваша организация.\n"
                "После этого проверяющие изучат заявку и вынесут решение."
            ),
            color=0x2ecc71
        )

        await channel.send(embed=embed)

        # -----------------------
        # 2️⃣ УПОМЯНУТЬ всех
        # -----------------------

        whitelist_mentions = " ".join(
            role.mention
            for role in (guild.get_role(r) for r in WHITELIST_ROLES)
            if role
        )

        await channel.send(f"{user.mention} {whitelist_mentions}")

        # Ответ пользователю
        await interaction.response.send_message(
            f"✅ Канал создан: {channel.mention}",
            ephemeral=True
        )


# ==============================
# View — ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
# ==============================

class ConfirmDeleteReg(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=15)
        self.author = author
        self.confirmed = False

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ Это не ваш канал!",
                ephemeral=True
            )
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message(
                "❌ Это не ваш канал!",
                ephemeral=True
            )
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


# ==============================
# SLASH: /setup_registration
# ==============================

@app_commands.command(
    name="setup_registration",
    description="Отправить сообщение с кнопкой регистрации предприятий."
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_registration(interaction: discord.Interaction):

    guild = interaction.guild
    channel = guild.get_channel(MESSAGE_CHANNEL_ID)

    if not channel:
        return await interaction.response.send_message(
            "❌ Канал для сообщений регистрации НЕ найден.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="🏢 Регистрация предприятий",
        description="Нажмите кнопку ниже, чтобы открыть приватный канал для регистрации.",
        color=0x3498db
    )

    await channel.send(embed=embed, view=RegistrationButton())

    await interaction.response.send_message(
        "✅ Сообщение с кнопкой отправлено!",
        ephemeral=True
    )


# ==============================
# SLASH: /delreg
# ==============================

@app_commands.command(
    name="delreg",
    description="Удалить ваш регистрационный канал."
)
async def delreg(interaction: discord.Interaction):

    channel = interaction.channel
    user = interaction.user

    if not isinstance(channel, discord.TextChannel) or not channel.name.startswith("регистрация-предприятия-"):
        return await interaction.response.send_message(
            "❌ Это не регистрационный канал!",
            ephemeral=True
        )

    # Проверка владельца канала
    username = user.name.lower().replace(" ", "-")
    if username not in channel.name:
        return await interaction.response.send_message(
            "❌ Только создатель может удалить этот канал!",
            ephemeral=True
        )

    embed = discord.Embed(
        title="⚠ Подтверждение удаления",
        description="Вы уверены, что хотите удалить этот канал?",
        color=0xff4444
    )

    view = ConfirmDeleteReg(user)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    await view.wait()

    if not view.confirmed:
        return

    # уведомление о таймере
    await interaction.followup.send(
        "🗑 Канал будет удалён через 5 секунд...",
        ephemeral=True
    )

    delete_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
    await discord.utils.sleep_until(delete_at)

    await channel.delete(reason=f"Удалён пользователем {user}")


# ==============================
# ФУНКЦИЯ ДЛЯ bot.py
# ==============================

async def setup_registration_commands(bot: commands.Bot):
    bot.add_view(RegistrationButton())  # чтобы кнопка работала после рестарта
    bot.tree.add_command(setup_registration)
    bot.tree.add_command(delreg)
