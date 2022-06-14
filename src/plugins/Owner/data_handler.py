from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class EventHandlerCog(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
