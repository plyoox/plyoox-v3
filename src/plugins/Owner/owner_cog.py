from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from .owner_commands import OwnerCommands

if TYPE_CHECKING:
    from main import Plyoox


class Owner(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    owner_commands = OwnerCommands()
