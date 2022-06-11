from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from lib import checks, helper
from lib.colors import DISCORD_DEFAULT
from lib.enums import PlyooxModule
from lib.types import LevelUserData
from translation import _
from ._helper import get_level_from_xp, get_level_xp

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.default_permissions()
@app_commands.guild_only
class LevelCommand(
    commands.GroupCog,
    group_name="level",
    group_description="Commands that are needed to interact with the level-system.",
):
    def __init__(self, bot: Plyoox):
        self.db = bot.db

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await checks.module_enabled_check(interaction, PlyooxModule.Leveling)

    @app_commands.command(name="rank", description="Shows information about the current rank of a member.")
    @app_commands.describe(member="The member from whom you want the rank.")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the current ranking information about a member. If no member is provided, the user that executed
        the command will be used.
        """
        guild = interaction.guild
        current_member = member or interaction.user
        lc = interaction.locale

        user_data: LevelUserData = await self.db.fetchrow(
            "SELECT * FROM leveling_users WHERE guild_id = $1 AND user_id = $2",
            guild.id,
            current_member.id,
        )

        if user_data is None:
            await helper.interaction_send(interaction, "level.rank.no_data")
            return

        current_level, remaining_xp = get_level_from_xp(user_data["xp"])
        required_xp = get_level_xp(current_level)

        embed = discord.Embed(color=DISCORD_DEFAULT)
        embed.set_author(name=str(current_member), icon_url=current_member.avatar)
        embed.add_field(name=_(lc, "level.rank.level"), value=f"> {current_level}", inline=False)
        embed.add_field(name=_(lc, "level.rank.xp"), value=f"> {remaining_xp}/{required_xp}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="show-roles", description="Shows the available level roles.")
    async def show_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        lc = interaction.locale
        guild = interaction.guild

        level_roles: list[list[int, int]] = await self.db.fetchval("SELECT roles FROM leveling WHERE id = $1", guild.id)
        if not level_roles:
            await helper.interaction_send(interaction, "level.level_roles.no_roles")
            return

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level} - {role.mention}")

        embed = discord.Embed(color=DISCORD_DEFAULT, title=_(lc, "level.level_roles.title"))
        embed.description = "\n".join(roles)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="Lists the top 10 users with the highest level on this guild.")
    async def top(self, interaction: Interaction):
        lc = interaction.locale
        guild = interaction.guild

        top_users = []

        while len(top_users) != 10:
            level_users = await self.db.fetch(
                "SELECT user_id, xp FROM leveling_users WHERE guild_id = $1 ORDER BY xp DESC LIMIT 15", guild.id
            )

            for level_user in level_users:
                member = guild.get_member(level_user["userId"])

                if member is not None:
                    current_level, current_xp = get_level_from_xp(level_user["xp"])
                    required_xp = get_level_xp(current_level)

                    top_users.append(
                        {"member": member, "level": current_level, "xp_progress": f"{current_xp}/{required_xp}"}
                    )

            if len(level_users) != 15:
                break

        if len(top_users) == 0:
            await helper.interaction_send(interaction, "level.top.no_users")
            return

        embed = discord.Embed(
            color=DISCORD_DEFAULT,
            title=_(lc, "level.top.title"),
        )

        for index, top_user in enumerate(top_users):
            embed.add_field(
                name=f"{index + 1}. {top_user['member'].display_name}",
                value=f"> {_(lc, 'level.top.level')} {top_user['level']}\n"
                f"> {top_user['xp_progress']} {_(lc, 'level.top.xp')}",
            )

        await interaction.response.send_message(embed=embed)
