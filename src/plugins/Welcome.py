from discord import Member
from discord.ext.commands import Cog

from ..main import Plyoox


class Welcome(Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        cache = await self.bot.get_cache(member.guild.id)
