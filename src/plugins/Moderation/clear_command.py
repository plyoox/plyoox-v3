import re
from typing import Optional

import discord
from discord import app_commands

from lib import checks
from translation import _
from utils import colors

LINK_REGEX = re.compile(r"https?://(?:[-\w.]|%[\da-fA-F]{2})+", re.IGNORECASE)


class ClearCommand(app_commands.Group):
    def __init__(self):
        super().__init__(name="clear", description="Clears messages in a channel. Specific filters can be applied.")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return checks.bot_permission_check(interaction, manage_messages=True, read_messages=True)

    @staticmethod
    async def do_removal(interaction: discord.Interaction, limit, *, reason, predicate):
        """This function is a helper to clear messages in an interaction channel.
        predicate must be a function (lambda) to specify the messages the bot should remove"""
        channel: discord.TextChannel = interaction.channel  # type: ignore
        lc = interaction.locale

        # delete the messages
        deleted_messages = await channel.purge(limit=limit, check=predicate, reason=reason)
        deleted_count = len(deleted_messages)
        affected_users = set(m.author.id for m in deleted_messages)  # list of affected users

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, title=_(lc, "moderation.clear.success_title"))
        embed.title = _(lc, "moderation.clear.success_title")

        embed.add_field(
            name=_(lc, "moderation.clear.deleted_messages"), value=f"> {deleted_count}/{limit}", inline=False
        )
        embed.add_field(name=_(lc, "moderation.clear.affected_users"), value=f"> {len(affected_users)}", inline=False)
        embed.add_field(name=_(lc, "reason"), value=f"> {reason or _(lc, 'no_reason')}", inline=False)

        # send the information to the user. the response has been deferred, so this uses followup
        await interaction.followup.send(_(lc, "moderation.successful_execution"), embed=embed)

    @app_commands.command(name="all", description="Clear all messages in a channel.")
    @app_commands.describe(
        amount="The amount of messages you want to purge.", reason="Why the messages should be deleted."
    )
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def clear_all(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        # first thing is to defer the response due to delay when deleting
        # lots of messages and sending logging information.
        await interaction.response.defer(ephemeral=True)

        # do the actual clearing
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: True)

    @app_commands.command(name="contains", description="Clears all messages that contain a specific string.")
    @app_commands.describe(
        amount="The number of messages the bot should scan through.",
        string="If this string is contained in a message, the bot will delete it.",
        reason="Why the messages should be deleted.",
    )
    async def clear_contains(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 500],
        string: str,
        reason: Optional[str],
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(
            interaction, amount, reason=reason, predicate=lambda m: string.lower() in m.content.lower()
        )

    @app_commands.command(name="user", description="Clears all messages from a specific user.")
    @app_commands.describe(
        amount="The number of messages the bot should scan through.",
        user="The user from whom the messages are to be deleted",
        reason="Why the messages should be deleted.",
    )
    async def clear_user(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 500],
        user: discord.User,
        reason: Optional[str],
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: m.author.id == user.id)

    @app_commands.command(name="links", description="Deletes all messages that contain a link.")
    @app_commands.describe(
        amount="The number of messages the bot should scan through.", reason="Why the messages should be deleted."
    )
    async def clear_links(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: LINK_REGEX.search(m.content))

    @app_commands.command(name="files", description="Deletes all messages that contains files.")
    @app_commands.describe(
        amount="The number of messages the bot should scan through.", reason="Why the messages should be deleted."
    )
    async def clear_files(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: len(m.attachments))
