from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from lib import formatting

if TYPE_CHECKING:
    from main import Plyoox

    from cache import WelcomeModel


class Welcome(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cache = await self.bot.cache.get_welcome(guild.id)

        if not cache or not cache.join_active:
            return

        # format message and send it
        if cache.join_message:
            channel = guild.get_channel(cache.join_channel)
            message = formatting.format_welcome_message(cache.join_message, member)

            if channel and channel.permissions_for(channel.guild.me).send_messages:
                await channel.send(
                    content=message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=True)
                )

            if cache.join_dm:
                try:
                    await member.send(message)
                except discord.Forbidden:
                    pass

        if not member.pending:
            await self._add_join_roles(cache, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        cache = await self.bot.cache.get_welcome(guild.id)

        if not cache or not cache.leave_active:
            return

        # format message and send it
        if cache.leave_message:
            channel = guild.get_channel(cache.leave_channel)

            if channel and channel.permissions_for(guild.me).send_messages:
                message = formatting.format_welcome_message(cache.leave_message, member)

                # send message and handle permission check
                await channel.send(
                    message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=True)
                )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.pending == after.pending:
            return

        cache = await self.bot.cache.get_welcome(before.guild.id)
        if not cache or not cache.join_active:
            return

        await self._add_join_roles(cache, after)

    @staticmethod
    async def _add_join_roles(cache: WelcomeModel, member: discord.Member):
        guild = member.guild

        if cache.join_roles and guild.me.guild_permissions.manage_roles:
            roles = []
            for role_id in cache.join_roles:
                role = guild.get_role(role_id)
                if role is not None and guild.me.top_role > role:
                    roles.append(role)

            if roles:
                await member.add_roles(*roles, reason="Adding join role")


async def setup(bot: Plyoox):
    await bot.add_cog(Welcome(bot))
