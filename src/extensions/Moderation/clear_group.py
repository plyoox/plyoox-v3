import asyncio
import re
import time
from typing import Optional, Callable

import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import extensions

LINK_REGEX = re.compile(r"https?://(?:[-\w.]|%[\da-fA-F]{2})+", re.IGNORECASE)


class CooldownByInteraction(commands.CooldownMapping):
    def _bucket_key(self, interaction: discord.Interaction) -> tuple[int, int, int]:
        return interaction.guild_id, interaction.user.id, interaction.channel.id


_cooldown_by_channel = CooldownByInteraction.from_cooldown(1, 15, commands.BucketType.channel)


class ClearGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="clear",
            description="Clears messages in a channel. Specific filters can be applied.",
            guild_only=True,
            default_permissions=discord.Permissions(manage_messages=True),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        perms = discord.Permissions(manage_messages=True, read_message_history=True, read_messages=True)
        if not interaction.app_permissions.is_superset(perms):
            raise app_commands.BotMissingPermissions(["manage_messages", "read_message_history", "read_messages"])

        bucket = _cooldown_by_channel.get_bucket(interaction)
        if bucket is None:
            return True

        retry_after = bucket.update_rate_limit(interaction.created_at.timestamp())
        if retry_after is None:
            return True

        raise app_commands.CommandOnCooldown(bucket, retry_after)

    @staticmethod
    async def _purge_helper(
        channel: discord.TextChannel,
        *,
        limit: Optional[int] = 100,
        check: Callable[[discord.Message], bool],
        reason: Optional[str] = None,
    ) -> list[discord.Message]:
        oldest_message_id = int((time.time() - 14 * 24 * 60 * 60) * 1000.0 - 1420070400000) << 22

        iterator = channel.history(limit=limit, after=discord.Object(id=oldest_message_id), oldest_first=False)
        ret: list[discord.Message] = []
        count = 0

        async for message in iterator:
            if count == 100:
                to_delete = ret[-100:]
                await channel.delete_messages(to_delete, reason=reason)
                count = 0
                await asyncio.sleep(1)

            if not check(message):
                continue

            count += 1
            ret.append(message)

        if count >= 2:
            to_delete = ret[-count:]
            await channel.delete_messages(to_delete, reason=reason)
        elif count == 1:
            await ret[-1].delete()

        return ret

    async def do_removal(
        self, interaction: discord.Interaction, limit: int, *, reason: str, predicate: Callable[[discord.Message], bool]
    ):
        """This function is a helper to clear messages in an interaction channel.
        predicate must be a function (lambda) to specify the messages the bot should remove"""
        channel: discord.TextChannel = interaction.channel

        # delete the messages
        deleted_messages = await self._purge_helper(channel, limit=limit, check=predicate, reason=reason)
        deleted_count = len(deleted_messages)

        if deleted_count == 0:
            await interaction.followup.send(
                interaction.translate(_("Cannot purge messages older than 14 days, due to Discord limitations."))
            )
            return

        affected_users = set(m.author.id for m in deleted_messages)  # list of affected users
        reason = reason or f"*{interaction.translate(_('No reason'))}*"

        embed = extensions.Embed(title=interaction.translate(_("Messages deleted")))

        embed.add_field(name=interaction.translate(_("Messages deleted")), value=f"> {deleted_count}/{limit}")
        embed.add_field(name=interaction.translate(_("Affected users")), value=f"> {len(affected_users)}")
        embed.add_field(
            name=interaction.translate(_("Reason")), value=f"> {reason}"
        )

        # Send the information to the user. The response has been deferred, so this uses followup
        await interaction.followup.send(
            interaction.translate(
                _("{message_count} Messages have been deleted."), data={"message_count": deleted_messages}
            ),
            embed=embed,
        )

    @app_commands.command(name="all", description=_("Clear all messages in a channel."))
    @app_commands.describe(
        amount=_("The amount of messages you want to purge."),
        reason=_("Why the messages should be deleted."),
    )
    async def clear_all(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        # first thing is to defer the response due to delay when deleting
        # lots of messages and sending logging information.
        await interaction.response.defer(ephemeral=True)

        # do the actual clearing
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda _: True)

    @app_commands.command(name="contains", description=("Clears all messages that contain a specific string."))
    @app_commands.describe(
        amount=_("The number of messages the bot should scan through."),
        string=_("If this string is contained in a message, the bot will delete it."),
        reason=_("Why the messages should be deleted."),
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

    @app_commands.command(name="user", description=_("Clears all messages from a specific user."))
    @app_commands.describe(
        amount=_("The number of messages the bot should scan through."),
        user=_("The user from whom the messages are to be deleted"),
        reason=_("Why the messages should be deleted."),
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

    @app_commands.command(name="links", description=_("Deletes all messages that contain a link."))
    @app_commands.describe(
        amount=_("The number of messages the bot should scan through."),
        reason=_("Why the messages should be deleted."),
    )
    async def clear_links(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(
            interaction, amount, reason=reason, predicate=lambda m: bool(LINK_REGEX.search(m.content))
        )

    @app_commands.command(name="files", description=_("Deletes all messages that contains files."))
    @app_commands.describe(
        amount=_("The number of messages the bot should scan through."),
        reason=_("Why the messages should be deleted."),
    )
    async def clear_files(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 500], reason: Optional[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.do_removal(interaction, amount, reason=reason, predicate=lambda m: bool(len(m.attachments)))
