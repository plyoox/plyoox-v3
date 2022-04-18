import discord.app_commands as cmds
from discord import Interaction
from discord.app_commands import AppCommandError

from lib import errors
from translation import _


class CommandTree(cmds.CommandTree):
    def __init__(self, bot):
        super().__init__(bot)

    async def on_error(self, interaction: Interaction, error: AppCommandError) -> None:
        if isinstance(error, errors.GuildOnly):
            await interaction.response.send_message(_(interaction.locale, "guild_only"))
