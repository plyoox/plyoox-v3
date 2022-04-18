from discord import Member
from discord.ext.commands import Cog

from src.main import Plyoox
from src.utils import format_messages


class Welcome(Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        cache = await self.bot.cache.get_welcome(member.id)
        guild = member.guild

        if not cache or not guild:
            return

        if not cache.active or not cache.join_active:
            return

        if cache.join_role and guild.me.guild_permissions.manage_roles:
            role = guild.get_role(cache.join_role)

            await member.add_roles(role, reason="Adding join role")

        if cache.join_message:
            channel = guild.get_channel(cache.join_channel)

            if channel.permissions_for(guild.me).send_messages:
                message = format_messages.format_welcome_message(cache.join_message, member)

                await channel.send(message)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        cache = await self.bot.cache.get_welcome(member.id)
        guild = member.guild

        if not cache or not guild:
            return

        if not cache.active or not cache.leave_active:
            return

        if cache.leave_message:
            channel = guild.get_channel(cache.leave_channel)

            if channel.permissions_for(guild.me).send_messages:
                message = format_messages.format_welcome_message(cache.leave_message, member)

                await channel.send(message)


def setup(bot: Plyoox):
    bot.add_cog(Welcome(bot))
