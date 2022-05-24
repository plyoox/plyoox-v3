from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class EventHandlerCog(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    def on_guild_remove(self, guild: discord.Guild):
        # Remove the guild cache
        self.bot.cache.remove_guild_cache(guild.id)
