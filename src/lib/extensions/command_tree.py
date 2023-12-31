from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _

from lib import errors

if TYPE_CHECKING:
    from main import Plyoox

_log = logging.getLogger(__name__)


class CommandTree(app_commands.CommandTree):
    def __init__(self, bot: Plyoox):
        super().__init__(bot)

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_translated(
                _("The command could not be found. If this error occurs more often, contact support."), ephemeral=True)
        elif isinstance(error, errors.ModuleDisabled):
            await interaction.response.send_message(error, ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_translated(
                _("Bot is missing permissions: {missing_permission}"),
                translation_data={"missing_permission": ", ".join(error.missing_permissions)},
                ephemeral=True,
            )
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(error, ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            pass
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_translated(
                _("Command is on cooldown, retry after {retry_after} seconds"),
                translation_data={"retry_after": round(error.retry_after)},
                ephemeral=True,
            )
        else:
            if isinstance(interaction.command, app_commands.Command):
                namespace = [interaction.command.name]
                command = interaction.command

                for _i in range(2):
                    if getattr(command, "parent", None):
                        namespace.append(command.parent.name)
                        command = command.parent

                namespace.reverse()

                _log.error(f"Ignoring exception in command `{' '.join(namespace)}`", exc_info=error)
            elif isinstance(interaction.command, app_commands.ContextMenu):
                _log.error(f"Ignoring exception in context menu `{interaction.command.name}`", exc_info=error)
