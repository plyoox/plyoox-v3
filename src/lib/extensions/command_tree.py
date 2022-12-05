import logging

import discord
from discord import app_commands

from lib import errors
from translation import _

_log = logging.getLogger(__name__)


class CommandTree(app_commands.CommandTree):
    def __init__(self, bot):
        super().__init__(bot)

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_message(_(interaction.locale, "errors.command_not_found"), ephemeral=True)
        elif isinstance(error, errors.ModuleDisabled):
            await interaction.response.send_message(error, ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                _(interaction.locale, "errors.bot_missing_permissions", errors=", ".join(error.missing_permissions))
            )
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(error, ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                _(interaction.locale, "errors.command_on_cooldown", retry_after=round(error.retry_after)),
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
