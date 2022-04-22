from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands

from lib import types, send_helper
from src.plugins.Leveling import helper
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

        current_level, remaining_xp = helper.get_level_from_xp(user_data["xp"])
        required_xp = helper.get_level_xp(current_level)

        embed = discord.Embed(color=colors.DISCORD_DEFAULT)
        embed.set_author(name=str(current_member), icon_url=current_member.avatar)
        embed.add_field(name=_(lc, "level.rank.level"), value=f"> {current_level}", inline=False)
        embed.add_field(name=_(lc, "level.rank.xp"), value=f"> {remaining_xp}/{required_xp}", inline=False)

        await interaction.response.send_message(embeds=[embed])

    @app_commands.command(name="level-roles", description="Shows the available level roles.")
    async def level_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        lc = interaction.locale
        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        level_roles: list[list[int]] = await bot.db.fetchval("SELECT roles FROM leveling WHERE id = $1", guild.id)
        if not level_roles:
            return await send_helper.interaction_send(interaction, "level.level_roles.no_roles")

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level}\t{role.mention}")

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, title=_(lc, "level.level_roles.title"))
        embed.description = "\n".join(roles)

        await interaction.response.send_message(embeds=[embed])
