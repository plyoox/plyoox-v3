from __future__ import annotations

import os
import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from lib.checks import owner_only
from lib.extensions import Embed
from translation import languages

if TYPE_CHECKING:
    from main import Plyoox


@owner_only()
class Owner(commands.GroupCog, group_name="owner", group_description="Owner only commands for managing the bot."):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    plugin_group = app_commands.Group(name="plugin", description="Managing the Plugin system.")

    @plugin_group.command(name="load", description="Loads a plugin")
    async def plugin_load(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.load_extension(plugin)
        except Exception:
            embed = Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully loaded.", ephemeral=True)

    @plugin_group.command(name="unload", description="Unloads a plugin")
    async def plugin_load(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." not in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.unload_extension(plugin)
        except Exception:
            embed = Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully unloaded.", ephemeral=True)

    @plugin_group.command(name="reload", description="Reloads a plugin")
    async def plugin_reload(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." not in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.reload_extension(plugin)
        except Exception:
            embed = Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully reloaded.", ephemeral=True)

    @app_commands.command(name="reload-language", description="Reloads the language files.")
    async def reload_language(self, interaction: discord.Interaction):
        languages._load_languages()

        await interaction.response.send_message("Language files successfully reloaded.", ephemeral=True)


async def setup(bot: Plyoox):
    if guild_id := os.getenv("OWNER_GUILD"):
        owner_guild = discord.Object(int(guild_id))
        await bot.add_cog(Owner(bot), guild=owner_guild)
