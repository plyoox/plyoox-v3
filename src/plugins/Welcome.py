import discord
from discord.ext import commands

from lib.formatting import format_welcome_message
from lib.helper import permission_check
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
        if cache.join_role and guild.me.guild_permissions.manage_roles:
            role = guild.get_role(cache.join_role)

            if role is not None:
                await member.add_roles(role, reason="Adding join role")

        # format message and send it
        if cache.join_message:
            channel = guild.get_channel(cache.join_channel)
            message = format_welcome_message(cache.join_message, member)

            # send message and handle permission check
            await permission_check(channel, content=message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cache = await self.bot.cache.get_welcome(member.id)
        guild = member.guild

        if cache is None:
            return

        # check if the settings have been disabled
        if not cache.active or not cache.leave_active:
            return

        # format message and send it
        if cache.leave_message:
            channel = guild.get_channel(cache.leave_channel)

            if channel.permissions_for(guild.me).send_messages:
                message = format_welcome_message(cache.leave_message, member)

                # send message and handle permission check
                await permission_check(channel, content=message)


async def setup(bot: Plyoox):
    await bot.add_cog(Welcome(bot))
