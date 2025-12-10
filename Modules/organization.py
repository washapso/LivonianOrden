import discord
from discord import app_commands
from discord.ext import commands

# ============================================
# РОЛЬ ПОМЕТКИ СОТРУДНИКОВ (работают в компании)
# ============================================

WORKER_ROLE_ID = 1448101935763685633


# =====================================================
#   РЕГИСТРАЦИЯ КОМАНД
# =====================================================

async def setup_organization_commands(bot: commands.Bot):
    bot.tree.add_command(create_org)
    bot.tree.add_command(hire_employee)
    bot.tree.add_command(fire_employee)
    bot.tree.add_command(delete_org)


# =====================================================
#   /create user name
# =====================================================

@app_commands.command(
    name="create",
    description="Создать организацию и назначить владельца."
)
@app_commands.describe(
    user="Кого назначить владельцем?",
    name="Название организации"
)
@app_commands.checks.has_permissions(administrator=True)
async def create_org(interaction: discord.Interaction, user: discord.Member, name: str):

    guild = interaction.guild
    worker_role = guild.get_role(WORKER_ROLE_ID)

    # Проверка — у пользователя уже есть организация
    if any(role.name.startswith("Владелец ") for role in user.roles):
        return await interaction.response.send_message(
            f"❌ {user.mention} уже владеет организацией!",
            ephemeral=True
        )

    # Проверка на существующую организацию
    if discord.utils.get(guild.roles, name=name):
        return await interaction.response.send_message(
            f"❌ Организация **{name}** уже существует.",
            ephemeral=True
        )

    # Создаём роли
    owner_role = await guild.create_role(
        name=f"Владелец {name}",
        color=discord.Color.gold()
    )

    employee_role = await guild.create_role(
        name=name,
        color=discord.Color.blue()
    )

    # Выдаём владельцу 3 роли:
    # 1) владелец компании
    # 2) сотрудник компании
    # 3) роль-пометка WORKER_ROLE
    await user.add_roles(owner_role, employee_role)
    if worker_role:
        await user.add_roles(worker_role)

    # Создаём категорию
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),

        owner_role: discord.PermissionOverwrite(
            view_channel=True,
            manage_channels=True,
            manage_permissions=True,
            send_messages=True,
            read_message_history=True
        ),

        employee_role: discord.PermissionOverwrite(
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

    category = await guild.create_category(
        name=f"📁 {name}",
        overwrites=overwrites
    )

    main_channel = await guild.create_text_channel(
        name="общий",
        category=category
    )

    # Ответ боту
    embed = discord.Embed(
        title="✅ Организация создана",
        description=f"Организация **{name}** успешно зарегистрирована!",
        color=0x2ecc71
    )
    embed.add_field(name="Владелец", value=user.mention)
    embed.add_field(name="Роли", value=f"{owner_role.mention}\n{employee_role.mention}\n{worker_role.mention if worker_role else ''}")
    embed.add_field(name="Категория", value=category.mention)

    await interaction.response.send_message(embed=embed)


# =====================================================
#   /hire — нанять сотрудника
# =====================================================

@app_commands.command(
    name="hire",
    description="Принять сотрудника в вашу организацию."
)
@app_commands.describe(user="Кого принять?")
async def hire_employee(interaction: discord.Interaction, user: discord.Member):

    author = interaction.user
    guild = interaction.guild
    worker_role = guild.get_role(WORKER_ROLE_ID)

    owner_roles = [r for r in author.roles if r.name.startswith("Владелец ")]
    if not owner_roles:
        return await interaction.response.send_message("❌ Вы не владелец.", ephemeral=True)

    org_name = owner_roles[0].name.replace("Владелец ", "")
    employee_role = discord.utils.get(guild.roles, name=org_name)

    if employee_role in user.roles:
        return await interaction.response.send_message("❌ Пользователь уже работает здесь.", ephemeral=True)

    await user.add_roles(employee_role)

    # Роль-пометка тоже выдаём
    if worker_role:
        await user.add_roles(worker_role)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="👤 Сотрудник принят",
            description=f"{user.mention} теперь работает в **{org_name}**.",
            color=0x2ecc71
        )
    )


# =====================================================
#   /fire — уволить сотрудника
# =====================================================

@app_commands.command(
    name="fire",
    description="Уволить сотрудника из вашей организации."
)
@app_commands.describe(user="Кого уволить?")
async def fire_employee(interaction: discord.Interaction, user: discord.Member):

    author = interaction.user
    guild = interaction.guild
    worker_role = guild.get_role(WORKER_ROLE_ID)

    owner_roles = [r for r in author.roles if r.name.startswith("Владелец ")]
    if not owner_roles:
        return await interaction.response.send_message("❌ Вы не владелец.", ephemeral=True)

    org_name = owner_roles[0].name.replace("Владелец ", "")
    employee_role = discord.utils.get(guild.roles, name=org_name)

    if employee_role not in user.roles:
        return await interaction.response.send_message("❌ Он не работает у вас.", ephemeral=True)

    await user.remove_roles(employee_role)

    # Проверяем: работает ли он ещё где-то?
    still_employee = any(
        role.name == r.name and not r.name.startswith("Владелец ")
        for r in user.roles
        for role in guild.roles
        if role.name == r.name
    )

    # Если не работает нигде → снимаем WORKER_ROLE
    if not still_employee and worker_role:
        await user.remove_roles(worker_role)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="📤 Сотрудник уволен",
            description=f"{user.mention} больше не работает в **{org_name}**.",
            color=0xe74c3c
        )
    )


# =====================================================
#   /delete_org — удаление организации (владелец + админ)
# =====================================================

class ConfirmDelete(discord.ui.View):
    def __init__(self, author, org_name, owner_role, employee_role, category, worker_role):
        super().__init__(timeout=15)
        self.author = author
        self.org_name = org_name
        self.owner_role = owner_role
        self.employee_role = employee_role
        self.category = category
        self.worker_role = worker_role
        self.confirmed = False

    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.red)
    async def confirm(self, interaction, _):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ Это не ваше действие.", ephemeral=True)
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction, _):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ Это не ваше действие.", ephemeral=True)
        self.stop()
        await interaction.response.defer()


@app_commands.command(
    name="delete_org",
    description="Удалить организацию полностью (владелец или администратор)."
)
@app_commands.describe(
    name="Название организации (только для администраторов)"
)
async def delete_org(interaction: discord.Interaction, name: str | None = None):

    author = interaction.user
    guild = interaction.guild
    worker_role = guild.get_role(WORKER_ROLE_ID)

    is_admin = author.guild_permissions.administrator

    # ========== Если вызывает владелец ==========
    if not is_admin:

        owner_roles = [r for r in author.roles if r.name.startswith("Владелец ")]
        if not owner_roles:
            return await interaction.response.send_message(
                "❌ Вы не владелец организации.", ephemeral=True
            )

        org_name = owner_roles[0].name.replace("Владелец ", "")

    # ========== Если вызывает администратор ==========
    else:
        if name is None:
            return await interaction.response.send_message(
                "❌ Укажите название организации: `/delete_org name:<Название>`",
                ephemeral=True
            )
        org_name = name

    # Поиск объектов организации
    owner_role = discord.utils.get(guild.roles, name=f"Владелец {org_name}")
    employee_role = discord.utils.get(guild.roles, name=org_name)
    category = discord.utils.get(guild.categories, name=f"📁 {org_name}")

    if not owner_role or not employee_role:
        return await interaction.response.send_message(
            "❌ Организация не найдена.",
            ephemeral=True
        )

    # Подтверждение
    view = ConfirmDelete(author, org_name, owner_role, employee_role, category, worker_role)

    embed = discord.Embed(
        title="⚠ Подтверждение удаления",
        description=f"Удалить организацию **{org_name}**?",
        color=0xff4444
    )

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    await view.wait()

    if not view.confirmed:
        return  # отмена

    # Удаляем каналы
    if category:
        for ch in category.channels:
            await ch.delete()
        await category.delete()

    # Удаляем роль-пометку у работников
    if employee_role and worker_role:
        for member in employee_role.members:
            await member.remove_roles(worker_role)

    # Удаляем роли организации
    if owner_role:
        await owner_role.delete()
    if employee_role:
        await employee_role.delete()

    await interaction.followup.send(
        embed=discord.Embed(
            title="🗑 Организация удалена",
            description=f"Организация **{org_name}** была полностью удалена.",
            color=0xff0000
        ),
        ephemeral=True
    )
