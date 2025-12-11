import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime

# ==============================
# НАСТРОЙКИ
# ==============================

MESSAGE_CHANNEL_ID = 1448079215219183779
REGISTRATION_CATEGORY_ID = 1448103698755485870
WHITELIST_ROLES = [1448012916115898560]

ARCHIVE_AFTER_HOURS = 24  # через сколько часов архивировать


# ==============================
# VIEW: ОДОБРИТЬ / ОТКЛОНИТЬ
# ==============================

class ReviewButtons(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, user: discord.Member, bot: commands.Bot):
        super().__init__(timeout=None)
        self.channel = channel
        self.user = user
        self.bot = bot
        self.cancel_delete = False  # флаг отмены удаления

    # =========================
    # ✔ ОДОБРИТЬ
    # =========================
    @discord.ui.button(label="✔ Одобрить", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, _):

        if not any(r.id in WHITELIST_ROLES for r in interaction.user.roles):
            return await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)

        await interaction.response.send_message(
            f"✅ Заявка одобрена!\n{self.user.mention}, пожалуйста напишите **название вашего предприятия** в чат.",
            ephemeral=False
        )

        def check(m: discord.Message):
            return m.author == self.user and m.channel == self.channel

        # Ждём сообщение с названием
        try:
            msg = await self.bot.wait_for("message", timeout=120, check=check)
            org_name = msg.content.strip()
        except asyncio.TimeoutError:
            return await self.channel.send("❌ Время вышло. Попробуйте снова.")

        # Подтверждение названия
        class ConfirmName(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.confirmed = None

            @discord.ui.button(label="Да", style=discord.ButtonStyle.green)
            async def yes(self, i, _):
                self.confirmed = True
                self.stop()
                await i.response.defer()

            @discord.ui.button(label="Нет", style=discord.ButtonStyle.red)
            async def no(self, i, _):
                self.confirmed = False
                self.stop()
                await i.response.defer()

        view = ConfirmName()
        await self.channel.send(
            f"Вы подтверждаете название: **{org_name}**?",
            view=view
        )

        await view.wait()

        if view.confirmed is None:
            return await self.channel.send("❌ Время подтверждения истекло.")

        if not view.confirmed:
            return await self.channel.send("🔁 Отправьте команду снова, чтобы выбрать другое название.")

        # Создаём организацию (используем функции внутри organization.py)
        from Modules.organization import create_organization_auto
        await create_organization_auto(self.channel.guild, self.user, org_name)

        await self.channel.send("🏗 Организация создана! Канал будет удалён…")
        await self.channel.delete(reason="Создано предприятие")

    # =========================
    # ✖ ОТКЛОНИТЬ
    # =========================
    @discord.ui.button(label="✖ Отклонить", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, _):

        if not any(r.id in WHITELIST_ROLES for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Нет прав!", ephemeral=True)

        await interaction.response.send_message("❌ Заявка отклонена. Канал удалится через **10 секунд**.\n"
                                               f"{self.user.mention}, введите `отмена`, чтобы остановить удаление.",
                                               ephemeral=False)

        self.cancel_delete = False

        def check(m: discord.Message):
            return m.channel == self.channel and m.author == self.user and m.content.lower() == "отмена"

        try:
            await self.bot.wait_for("message", timeout=10, check=check)
            self.cancel_delete = True
            return await self.channel.send("⛔ Удаление отменено пользователем.")
        except asyncio.TimeoutError:
            pass

        if not self.cancel_delete:
            await self.channel.send("🗑 Время истекло. Удаляю канал…")
            await self.channel.delete(reason="Отклонено проверяющим")


# ==============================
# VIEW: КНОПКА СОЗДАТЬ КАНАЛ
# ==============================

class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Создать канал",
        style=discord.ButtonStyle.green,
        custom_id="registration_create_channel"
    )
    async def create_channel(self, interaction: discord.Interaction, button):

        guild = interaction.guild
        user = interaction.user

        channel_name = f"регистрация-предприятия-{user.name}".lower().replace(" ", "-")

        if discord.utils.get(guild.channels, name=channel_name):
            return await interaction.response.send_message(
                "❌ У вас уже есть канал регистрации.",
                ephemeral=True
            )

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

        for rid in WHITELIST_ROLES:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

        category = guild.get_channel(REGISTRATION_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            category = None

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        # --- EMBED --- #
        embed = discord.Embed(
            title="📄 Регистрация предприятия",
            description=(
                "Опишите, чем будет заниматься ваша организация.\n"
                "Проверяющие изучат вашу заявку."
            ),
            color=0x2ecc71
        )
        await channel.send(embed=embed)

        # --- Ping --- #
        wl_mentions = " ".join(
            guild.get_role(r).mention for r in WHITELIST_ROLES if guild.get_role(r)
        )
        await channel.send(f"{user.mention} {wl_mentions}")

        # --- Добавляем кнопки для проверки --- #
        await channel.send(
            "**Проверяющие:** используйте кнопки ниже для вынесения решения:",
            view=ReviewButtons(channel, user)
        )

        await interaction.response.send_message(
            f"✅ Канал создан: {channel.mention}",
            ephemeral=True
        )


# ==============================
# VIEW: ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
# ==============================

class ConfirmDeleteReg(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=10)
        self.author = author
        self.confirmed = False

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red)
    async def confirm(self, interaction, _):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ Не ваш канал.", ephemeral=True)
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction, _):
        if interaction.user != self.author:
            return
        self.stop()
        await interaction.response.defer()


# ==============================
# SLASH: /setup_registration
# ==============================

@app_commands.command(name="setup_registration", description="Создать меню регистрации предприятий.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_registration(interaction):

    channel = interaction.guild.get_channel(MESSAGE_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)

    embed = discord.Embed(
        title="🏢 Регистрация предприятий",
        description="Нажмите кнопку, чтобы подать заявку.",
        color=0x3498db
    )

    await channel.send(embed=embed, view=RegistrationButton())
    await interaction.response.send_message("✅ Отправлено.", ephemeral=True)


# ==============================
# SLASH: /delreg
# ==============================

@app_commands.command(name="delreg", description="Удалить свой регистрационный канал.")
async def delreg(interaction):

    channel = interaction.channel
    user = interaction.user

    if not channel.name.startswith("регистрация-предприятия-"):
        return await interaction.response.send_message(
            "❌ Это не регистрационный канал.", ephemeral=True
        )

    if user.name.lower().replace(" ", "-") not in channel.name:
        return await interaction.response.send_message(
            "❌ Вы не владелец этого канала.", ephemeral=True
        )

    embed = discord.Embed(
        title="⚠ Подтверждение",
        description="Удалить канал?",
        color=0xff4444
    )

    view = ConfirmDeleteReg(user)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    await view.wait()

    if not view.confirmed:
        return

    await interaction.followup.send("🗑 Удаляю через 5 секунд...", ephemeral=True)

    delete_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
    await discord.utils.sleep_until(delete_at)

    await channel.delete(reason=f"Удалено пользователем {user}")


# ==============================
# АВТО-АРХИВАЦИЯ КАНАЛОВ
# ==============================

async def archive_channel(channel: discord.TextChannel):

    archived_name = f"архив-{channel.name}"
    await channel.edit(name=archived_name)

    # Закрываем пользователю канал
    for overwrite_target, perms in channel.overwrites.items():
        if isinstance(overwrite_target, discord.Member):
            await channel.set_permissions(overwrite_target, view_channel=False)

    await channel.send("📦 Канал был автоматически архивирован из-за неактивности.")


@tasks.loop(hours=1)
async def check_archives(bot):

    now = datetime.datetime.utcnow()

    for guild in bot.guilds:
        for channel in guild.text_channels:

            if not channel.name.startswith("регистрация-предприятия-"):
                continue

            last_msg = channel.last_message
            if not last_msg:
                continue

            if (now - last_msg.created_at).total_seconds() >= ARCHIVE_AFTER_HOURS * 3600:
                await archive_channel(channel)


# ==============================
# РЕГИСТРАЦИЯ В bot.py
# ==============================

async def setup_registration_commands(bot: commands.Bot):
    bot.add_view(RegistrationButton())
    bot.tree.add_command(setup_registration)
    bot.tree.add_command(delreg)

    # Автоархивация запускается при старте
    check_archives.start(bot)
