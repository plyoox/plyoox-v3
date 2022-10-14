from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class Tags(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    tag_group = app_commands.Group(name="tag", description="Useful commands to view and manage tags.")

    @app_commands.command(name="tag-create", description="Creates a new tag.")
    @app_commands.default_permissions()
    @app_commands.guild_only
    async def create_tag(self, interaction: discord.Interaction, name: app_commands.Range[str, 2, 32]):
        tag_owner = await self.bot.db.fetchval(
            "SELECT author_id FROM tags WHERE guild_id = $1 AND name = $2", interaction.guild_id, name.lower()
        )

        if tag_owner is not None:
            pass





async def setup(bot: Plyoox):
    await bot.add_cog(Tags(bot))
