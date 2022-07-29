import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from lib.checks import owner_only

if TYPE_CHECKING:
    from main import Plyoox


@owner_only()
class OwnerCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="owner", description="Owner only commands for managing the bot.")

    plugin_group = app_commands.Group(name="plugin", description="Managing the Plugin system.")

    @plugin_group.command(name="load", description="Loads a plugin")
    async def plugin_load(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.load_extension(plugin)
        except Exception:
            embed = discord.Embed(description=f"```py\n{traceback.format_exc()}```")
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
            embed = discord.Embed(description=f"```py\n{traceback.format_exc()}```")
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
            embed = discord.Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully reloaded.", ephemeral=True)
