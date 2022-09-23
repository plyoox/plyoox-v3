from typing import TYPE_CHECKING

from discord import app_commands

if TYPE_CHECKING:
    import discord


class ModuleDisabled(app_commands.AppCommandError):
    pass


class AnilistQueryError(app_commands.AppCommandError):
    pass


class ConversionError(app_commands.AppCommandError):
    if TYPE_CHECKING:
        interaction: discord.Interaction

    pass
