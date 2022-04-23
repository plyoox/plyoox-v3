from __future__ import annotations

import random
import time
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from lib import formatting, send_helper, utils
from plugins.Leveling import level_commands, leveling_helper

if TYPE_CHECKING:
    from src.main import Plyoox
    from lib.types import LevelUserData


class Leveling(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._users_on_cooldown = defaultdict(lambda: utils.ExpiringCache(seconds=60))

    leveling_commands = level_commands.LevelingCommands()

    async def _fetch_member_data(self, member: discord.Member) -> LevelUserData:
        """Fetches the leveling data of a member."""
        return await self.bot.db.fetchrow(
            'SELECT * FROM leveling_users WHERE "guildId" = $1 AND "userId" = $2',
            member.guild.id,
            member.id,
        )

    async def _create_member_data(self, member: discord.Member, xp: int) -> None:
        """Creates a database entry for the member."""
        await self.bot.db.execute(
            'INSERT INTO leveling_users ("guildId", "userId", xp) VALUES ($1, $2, $3)',
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
        if self._users_on_cooldown[guild.id].get(member.id):
            print("cooldown")
            return

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

        self._users_on_cooldown[guild.id][member.id] = time.time()  # set user on cooldown
        message_xp = random.randint(15, 25)  # generate a random amount of xp between 15 and 25
        member_data = await self._fetch_member_data(member)

        # member has no data saved
        if member_data is None:
            return await self._create_member_data(member, message_xp)

        await self._update_member_data(member_data["id"], message_xp)

        before_level = leveling_helper.get_level_from_xp(member_data["xp"])[0]  # level with the current xp
        after_level = leveling_helper.get_level_from_xp(member_data["xp"] + message_xp)[0]  # level with the added xp

        if before_level != after_level:
            # highest role that will be added
            # only needed for the leveling message
            highest_add_role = None

            # only add role if available and the bot has proper permissions
            if len(cache.roles) and guild.me.guild_permissions.manage_roles:
                add_role_id = list(filter(lambda r: r[1] == after_level if r else False, cache.roles))
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
                    await send_helper.permission_check(channel, content=level_message)
                else:
                    level_channel = guild.get_channel(cache.channel)

                    await send_helper.permission_check(level_channel, content=level_message)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Removes the leveling cooldown cache of guilds the bot left. This prevents
        having lots of dead guilds in the cache.
        """
        try:
            del self._users_on_cooldown[guild.id]
        except KeyError:
            pass
