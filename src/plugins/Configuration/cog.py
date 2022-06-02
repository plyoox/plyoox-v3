from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext import commands

from .welcome import WelcomeConfig

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.guild_only
@app_commands.default_permissions(administrator=True)
class Configuration(
    commands.GroupCog, group_name="configuration", group_description="Setup the bot with simple commands."
):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    welcome_group = WelcomeConfig()
