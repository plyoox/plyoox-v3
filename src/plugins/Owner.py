from __future__ import annotations

import contextlib
import io
import os
import textwrap
import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands, ui
from discord.ext import commands

from lib import checks, extensions
from translation import languages

if TYPE_CHECKING:
    from main import Plyoox


class ExecuteModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Execute Code")

    code = ui.TextInput(label="Python Code", required=True, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        env = {
            "bot": interaction.client,
            "interaction": interaction,
        }

        env.update(globals())

        body = self.code.value
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            await interaction.followup.send(f"```py\n{e.__class__.__name__}: {e}\n```")
            return

        func = env["func"]
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await interaction.followup.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    await interaction.followup.send(f"```py\n{value}\n```")
            else:
                await interaction.followup.send(f"```py\n{value}{ret}\n```")


class Owner(commands.GroupCog, group_name="owner", group_description="Owner only commands for managing the bot."):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    plugin_group = app_commands.Group(
        name="plugin", description="Managing the Plugin system.", auto_locale_strings=False
    )

    @plugin_group.command(name="load", description="Loads a plugin", auto_locale_strings=False)
    @checks.owner_only()
    async def plugin_load(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.load_extension(plugin)
        except Exception:
            embed = extensions.Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully loaded.", ephemeral=True)

    @plugin_group.command(name="unload", description="Unloads a plugin", auto_locale_strings=False)
    @checks.owner_only()
    async def plugin_load(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." not in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.unload_extension(plugin)
        except Exception:
            embed = extensions.Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully unloaded.", ephemeral=True)

    @plugin_group.command(name="reload", description="Reloads a plugin", auto_locale_strings=False)
    @checks.owner_only()
    async def plugin_reload(self, interaction: discord.Interaction, plugin: str):
        bot: Plyoox = interaction.client  # type: ignore

        if "." not in plugin:
            plugin = f"plugins.{plugin}"

        try:
            await bot.reload_extension(plugin)
        except Exception:
            embed = extensions.Embed(description=f"```py\n{traceback.format_exc()}```")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Plugin successfully reloaded.", ephemeral=True)

    @app_commands.command(name="reload-language", description="Reloads the language files.", auto_locale_strings=False)
    @checks.owner_only()
    async def reload_language(self, interaction: discord.Interaction):
        languages._load_languages()

        await interaction.response.send_message("Language files successfully reloaded.", ephemeral=True)

    @app_commands.command(name="execute", description="Executes python code.", auto_locale_strings=False)
    @checks.owner_only()
    async def execute(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ExecuteModal())


async def setup(bot: Plyoox):
    if guild_id := os.getenv("OWNER_GUILD"):
        owner_guild = discord.Object(int(guild_id))
        await bot.add_cog(Owner(bot), guild=owner_guild)
