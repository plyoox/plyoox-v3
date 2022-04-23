from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from src.plugins.Owner import owner_commands

if TYPE_CHECKING:
    from src.main import Plyoox


class Owner(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    owner_commands = owner_commands.OwnerCommands()
