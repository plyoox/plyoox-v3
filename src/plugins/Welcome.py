import discord
from discord.ext import commands

from lib import formatting, helper
from main import Plyoox


class Welcome(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cache = await self.bot.cache.get_welcome(member.id)
        guild = member.guild

        if cache is None:
            return

        # check if the settings have been disabled
        if not cache.active or not cache.join_active:
            return

        # only add role if the bot has the permissions
        if cache.join_roles and guild.me.guild_permissions.manage_roles:
            if member.pending:
                return

            roles = []
            for role_id in cache.join_roles:
                role = guild.get_role(role_id)
                if role is not None:
                    roles.append(role)

            if roles:
                await member.add_roles(*roles, reason="Adding join role")

        # format message and send it
        if cache.join_message:
            channel = guild.get_channel(cache.join_channel)
            message = formatting.format_welcome_message(cache.join_message, member)

            # send message and handle permission check
            await helper.permission_check(channel, content=message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        cache = await self.bot.cache.get_welcome(guild.id)

        if cache is None:
            return

        # check if the settings have been disabled
        if not cache.active or not cache.leave_active:
            return

        # format message and send it
        if cache.leave_message:
            channel = guild.get_channel(cache.leave_channel)

            if channel.permissions_for(guild.me).send_messages:
                message = formatting.format_welcome_message(cache.leave_message, member)

                # send message and handle permission check
                await helper.permission_check(channel, content=message)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.pending == after.pending:
            return

        guild = before.guild
        cache = await self.bot.cache.get_welcome(guild.id)

        if cache is None:
            return

        if cache.join_roles and guild.me.guild_permissions.manage_roles:
            roles = []
            for role_id in cache.join_roles:
                role = guild.get_role(role_id)
                if role is not None:
                    roles.append(role)

            if roles:
                await after.add_roles(*roles, reason="Adding join role")


async def setup(bot: Plyoox):
    await bot.add_cog(Welcome(bot))
