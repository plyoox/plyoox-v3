from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class EventHandlerCog(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.db.execute("INSERT INTO guild_config (id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)

    @app_commands.command(
        name="guild-registration",
        description="Registers the guild for the bot. This is only needed when the bot was invited while it was offline.",
    )
    @app_commands.guild_only
    @app_commands.default_permissions(administrator=True)
    async def register_guild(self, interaction: discord.Interaction):
        await self.bot.db.execute(
            "INSERT INTO guild_config (id) VALUES ($1) ON CONFLICT DO NOTHING", interaction.guild_id
        )
        await interaction.response.send_message("Guild registered.", ephemeral=True)


async def setup(bot: Plyoox):
    await bot.add_cog(EventHandlerCog(bot))
