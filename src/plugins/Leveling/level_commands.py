from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands, Interaction

from lib import types, send_helper
from plugins.Leveling import leveling_helper
from translation import _
from utils import colors

if TYPE_CHECKING:
    from src.main import Plyoox


class LevelingCommands(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="level",
            description="Commands that are needed to interact with the level-system.",
        )

    @app_commands.command(name="rank", description="Shows information about the current rank of a member.")
    @app_commands.describe(member="The member from whom you want the rank.")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the current ranking information about a member. If no member is provided, the user that executed
        the command will be used.
        """
        bot: Plyoox = interaction.client  # type: ignore
        guild = interaction.guild
        current_member = member or interaction.user
        lc = interaction.locale

        user_data: types.LevelUserData = await bot.db.fetchrow(
            'SELECT * FROM leveling_users WHERE "guildId" = $1 AND "userId" = $2',
            guild.id,
            current_member.id,
        )

        if user_data is None:
            return await send_helper.interaction_send(interaction, "level.rank.no_data")

        current_level, remaining_xp = leveling_helper.get_level_from_xp(user_data["xp"])
        required_xp = leveling_helper.get_level_xp(current_level)

        embed = discord.Embed(color=colors.DISCORD_DEFAULT)
        embed.set_author(name=str(current_member), icon_url=current_member.avatar)
        embed.add_field(name=_(lc, "level.rank.level"), value=f"> {current_level}", inline=False)
        embed.add_field(name=_(lc, "level.rank.xp"), value=f"> {remaining_xp}/{required_xp}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="show-roles", description="Shows the available level roles.")
    async def show_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        lc = interaction.locale
        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        level_roles: list[list[int, int]] = await bot.db.fetchval("SELECT roles FROM leveling WHERE id = $1", guild.id)
        if not level_roles:
            return await send_helper.interaction_send(interaction, "level.level_roles.no_roles")

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level} - {role.mention}")

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, title=_(lc, "level.level_roles.title"))
        embed.description = "\n".join(roles)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reset-level", description="Resets the level of a member. This action cannot be undone.")
    @app_commands.describe(member="The member from whom you want to reset rank.")
    async def reset_level(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        bot: Plyoox = interaction.client  # type: ignore

        await bot.db.execute(
            'DELETE FROM leveling_users WHERE "userId" = $1 AND "guildId" = $2', member.id, interaction.guild.id
        )

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, description=_(lc, "level.reset_level.level_reset"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="top", description="Lists the top 10 users with the highest level on this guild.")
    async def top(self, interaction: Interaction):
        lc = interaction.locale
        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        top_users = []

        while len(top_users) != 10:
            level_users = await bot.db.fetch(
                'SELECT "userId", xp FROM leveling_users WHERE "guildId" = $1 ORDER BY xp DESC LIMIT 15', guild.id
            )

            for level_user in level_users:
                member = guild.get_member(level_user["userId"])

                if member is not None:
                    current_level, current_xp = leveling_helper.get_level_from_xp(level_user["xp"])
                    required_xp = leveling_helper.get_level_xp(current_level)

                    top_users.append(
                        {"member": member, "level": current_level, "xp_progress": f"{current_xp}/{required_xp}"}
                    )

            if len(level_users) != 15:
                break

        if len(top_users) == 0:
            return await send_helper.interaction_send(interaction, "level.top.no_users")

        embed = discord.Embed(
            color=colors.DISCORD_DEFAULT,
            title=_(lc, "level.top.title"),
        )

        for index, top_user in enumerate(top_users):
            embed.add_field(
                name=f"{index + 1}. {top_user['member'].display_name}",
                value=f"> {_(lc, 'level.top.level')} {top_user['level']}\n"
                f"> {top_user['xp_progress']} {_(lc, 'level.top.xp')}",
            )

        await interaction.response.send_message(embed=embed)
