import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from lib import extensions
from translation import _


_T = app_commands.locale_str
LINK_REGEX = re.compile(r"https?://(?:[-\w.]|%[\da-fA-F]{2})+", re.IGNORECASE)


class CooldownByInteraction(commands.CooldownMapping):
    def _bucket_key(self, interaction: discord.Interaction) -> tuple[int, int]:
        return interaction.guild_id, interaction.user.id


_cooldown_by_user = CooldownByInteraction.from_cooldown(3, 60, commands.BucketType.member)


@app_commands.checks.bot_has_permissions(manage_messages=True)
class ClearGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="clear",
            description="Clears messages in a channel. Specific filters can be applied.",
            guild_only=True,
            default_permissions=discord.Permissions(manage_messages=True),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        bucket = _cooldown_by_user.get_bucket(interaction)
        if bucket is None:
            return True

        retry_after = bucket.update_rate_limit(interaction.created_at.timestamp())
        if retry_after is None:
            return True

        raise app_commands.CommandOnCooldown(bucket, retry_after)

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

        embed = extensions.Embed(title=_(lc, "moderation.clear.success_title"))
        embed.title = _(lc, "moderation.clear.success_title")

        embed.add_field(name=_(lc, "moderation.clear.deleted_messages"), value=f"> {deleted_count}/{limit}")
        embed.add_field(name=_(lc, "moderation.clear.affected_users"), value=f"> {len(affected_users)}")
        embed.add_field(name=_(lc, "reason"), value=f"> {reason or _(lc, 'no_reason')}")

        # send the information to the user. the response has been deferred, so this uses followup
        await interaction.followup.send(_(lc, "moderation.successful_execution"), embed=embed)

    @app_commands.command(name="all", description="Clear all messages in a channel.")
    @app_commands.describe(
        amount="The amount of messages you want to purge.",
        reason=_T("Why the messages should be deleted.", key="clear.reason"),
    )
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
        amount=_T("The number of messages the bot should scan through.", key="clear.amount"),
        string="If this string is contained in a message, the bot will delete it.",
        reason=_T("Why the messages should be deleted.", key="clear.reason"),
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
        amount=_T("The number of messages the bot should scan through.", key="clear.amount"),
        user="The user from whom the messages are to be deleted",
        reason=_T("Why the messages should be deleted.", key="clear.reason"),
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
        amount=_T("The number of messages the bot should scan through.", key="clear.amount"),
        reason=_T("Why the messages should be deleted.", key="clear.reason"),
    )
    async def clear_links(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: LINK_REGEX.search(m.content))

    @app_commands.command(name="files", description="Deletes all messages that contains files.")
    @app_commands.describe(
        amount=_T("The number of messages the bot should scan through.", key="clear.amount"),
        reason=_T("Why the messages should be deleted.", key="clear.reason"),
    )
    async def clear_files(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: len(m.attachments))
