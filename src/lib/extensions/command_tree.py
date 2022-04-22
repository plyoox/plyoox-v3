import discord
from discord import app_commands

from lib import errors
from translation import _


class CommandTree(app_commands.CommandTree):
    def __init__(self, bot):
        super().__init__(bot)

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, errors.GuildOnly):
            await interaction.response.send_message(_(interaction.locale, "guild_only"))
