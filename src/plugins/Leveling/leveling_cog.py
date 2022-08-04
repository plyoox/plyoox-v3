from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from lib import formatting, helper, extensions
from translation import _
from . import _helper, level_group

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import LevelUserData


class Leveling(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._cooldown_by_user = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.member)

    level_commands = level_group.LevelGroup()

    async def _fetch_member_data(self, member: discord.Member) -> LevelUserData:
        """Fetches the leveling data of a member."""
        return await self.bot.db.fetchrow(
            "SELECT * FROM leveling_users WHERE guild_id = $1 AND user_id = $2",
            member.guild.id,
            member.id,
        )

    async def _create_member_data(self, member: discord.Member, xp: int) -> None:
        """Creates a database entry for the member."""
        await self.bot.db.execute(
            "INSERT INTO leveling_users (guild_id, user_id, xp) VALUES ($1, $2, $3)",
            member.guild.id,
            member.id,
            xp,
        )

    async def _update_member_data(self, id: int, xp: int) -> None:
        """Adds a specific amount of xp to the user in the database."""
        await self.bot.db.execute("UPDATE leveling_users SET xp = xp + $1 WHERE id = $2", xp, id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore dm's and other bots
        if message.guild is None or message.author.bot:
            return

        member = message.author
        channel = message.channel
        guild = message.guild

        # user is on cooldown
        bucket = self._cooldown_by_user.get_bucket(message)
        if bucket.update_rate_limit(message.created_at.timestamp()):
            return False

        cache = await self.bot.cache.get_leveling(guild.id)

        # leveling is deactivated on this guild
        if cache is None or not cache.active:
            return

        # ignore no xp channels
        if channel.id in cache.no_xp_channels:
            return

        # ignore members with the no xp role
        if cache.no_xp_role in member._roles:
            return

        message_xp = random.randint(15, 25)  # generate a random amount of xp between 15 and 25
        member_data = await self._fetch_member_data(member)

        # member has no data saved
        if member_data is None:
            await self._create_member_data(member, message_xp)
            return

        await self._update_member_data(member_data["id"], message_xp)

        before_level = _helper.get_level_from_xp(member_data["xp"])[0]  # level with the current xp
        after_level = _helper.get_level_from_xp(member_data["xp"] + message_xp)[0]  # level with the added xp

        if before_level != after_level:
            # highest role that will be added
            # only needed for the leveling message
            highest_add_role = None

            # only add role if available and the bot has proper permissions
            if len(cache.roles) and guild.me.guild_permissions.manage_roles:
                add_role_id = list(filter(lambda r: r[1] == after_level, cache.roles))
                highest_add_role = guild.get_role(add_role_id[0][0])

                if cache.remove_roles and highest_add_role:
                    try:
                        await member.add_roles(highest_add_role, reason="Add new level role")

                        remove_roles = []

                        # adds the roles that should be removed to a list
                        # that are all roles that are not for the current level
                        for [role_id, level] in cache.roles:
                            if level == after_level:
                                continue

                            new_role = guild.get_role(role_id)
                            if new_role is not None:
                                remove_roles.append(new_role)

                        await member.remove_roles(*remove_roles, reason="Remove old level roles")
                    except discord.Forbidden:
                        pass
                else:
                    add_lvl_roles = []

                    # adds all roles that are for the current level or below
                    for [role_id, role_level] in cache.roles:
                        if role_id in member._roles:
                            continue

                        if role_level > after_level:
                            continue

                        new_role = guild.get_role(role_id)
                        if new_role is not None:
                            add_lvl_roles.append(new_role)

                    try:
                        await member.add_roles(*add_lvl_roles, reason="Add new level roles")
                    except discord.Forbidden:
                        pass

            if cache.message:
                # format the messages with the variables
                f_level = formatting.LevelFormatObject(level=after_level, role=highest_add_role)

                level_message = formatting.format_leveling_message(cache.message, member=member, level=f_level)

                # if a channel is given send the message to it
                # else the message will be sent to the current channel
                if cache.channel is None:
                    await helper.permission_check(channel, content=level_message)
                else:
                    level_channel = guild.get_channel(cache.channel)

                    await helper.permission_check(level_channel, content=level_message)

    @app_commands.command(name="reset-level", description="Resets the level of a member. This action cannot be undone.")
    @app_commands.describe(member="The member from whom you want to reset rank.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def reset_level(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        guild = interaction.guild

        await self.bot.db.execute(
            "DELETE FROM leveling_users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id
        )

        if guild.me.guild_permissions.manage_roles:
            leveling_cache = await self.bot.cache.get_leveling(guild.id)
            if leveling_cache is not None:
                if leveling_cache.roles:
                    roles_to_remove = []
                    for [role_id, level] in leveling_cache.roles:
                        if role_id in member._roles:
                            roles_to_remove.append(discord.Object(id=role_id))

                    await member.remove_roles(*roles_to_remove, reason=_(lc, "level.reset_level.reset_reason"))

        embed = extensions.Embed(description=_(lc, "level.reset_level.success"))
        await interaction.response.send_message(embed=embed, ephemeral=True)
