import logging

import discord
from discord import app_commands
from discord.app_commands import locale_str as _

from lib import errors
from translation.translator import translate

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
                translate(_("Bot is missing permissions: {missing_permission}"), self.bot, interaction.locale).format(
                    permissions=", ".join(error.missing_permissions),
                ),
                ephemeral=True,
            )
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(error, ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            pass
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                translate(
                    _("Command is on cooldown, retry after {retry_after} seconds"), self.bot, interaction.locale
                ).format(
                    retry_after=round(error.retry_after),
                ),
                ephemeral=True,
            )
        else:
            if isinstance(interaction.command, app_commands.Command):
                namespace = [interaction.command.name]
                command = interaction.command

                for _ in range(2):
                    if getattr(command, "parent", None):
                        namespace.append(command.parent.name)
                        command = command.parent

                namespace.reverse()

                _log.error(f"Ignoring exception in command `{' '.join(namespace)}`", exc_info=error)
            elif isinstance(interaction.command, app_commands.ContextMenu):
                _log.error(f"Ignoring exception in context menu `{interaction.command.name}`", exc_info=error)
