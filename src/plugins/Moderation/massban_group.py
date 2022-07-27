from __future__ import annotations

import datetime
import re
from typing import Union, Optional

import discord
from discord import app_commands, ui

from lib import emojis
from lib.extensions import Embed
from translation import _


def can_execute_action(interaction: discord.Interaction, user: discord.Member, target: discord.Member):
    return user.id == interaction.client.owner_id or user == interaction.guild.owner or user.top_role > target.top_role  # type: ignore


async def _change_member_view(interaction: discord.Interaction, view: MemberView, index_change: int = 0):
    lc = interaction.locale

    view.current_index += index_change

    embed = Embed(title=_(lc, "moderation.massban.view_member_title"))
    embed.set_footer(text=f"{_(lc, 'moderation.massban.page')}: {view.current_index + 1}")

    members = view.members[
        view.current_index * MemberView.MEMBERS_PER_PAGE : MemberView.MEMBERS_PER_PAGE * (view.current_index + 1)
    ]

    embed.description = "\n".join(f"{m} ({m.id})" for m in members)  # type: ignore

    await interaction.response.defer()
    await interaction.edit_original_message(embed=embed, view=MemberView(view._view, lc))


class BanButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.ban_button_label"), style=discord.ButtonStyle.red, emoji=emojis.hammer
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        lc = interaction.locale

        await interaction.response.send_message(
            _(lc, "moderation.massban.ban_users", member_count=len(self._view.members))
        )

        error_count = 0
        ban_count = 0

        for member in self._view.members:
            try:
                await interaction.guild.ban(member, reason=self._view.reason)
                ban_count += 1
            except discord.Forbidden:
                error_count += 1
                if error_count == 5:
                    await interaction.edit_original_message(
                        content=_(lc, "moderation.massban.ban_failed", member_count=ban_count)
                    )
                    return
            except discord.HTTPException:
                pass

        await interaction.edit_original_message(content=_(lc, "moderation.massban.ban_success", member_count=ban_count))


class CancelButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.close_button_label"), style=discord.ButtonStyle.gray, emoji=emojis.close
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        lc = interaction.locale

        for item in self._view.children:
            item.disabled = True

        await interaction.response.defer()
        await interaction.edit_original_message(content=_(lc, "moderation.massban.cancel_ban"), view=None, embed=None)


class ViewMemberButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.view_member_button_label"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.users,
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, MemberView(view=self._view, locale=interaction.locale))


class NextMemberButton(ui.Button):
    def __init__(self, view: MemberView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "moderation.massban.next_member_button_label"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevron_right,
            disabled=disabled,
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, self._view, 1)


class BackMemberButton(ui.Button):
    def __init__(self, view: MemberView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "moderation.massban.last_member_button_label"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevron_left,
            disabled=disabled,
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, self._view, -1)


class CloseMemberViewButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.close_view_members_button_label"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.close,
        )

        self._view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = Embed(description=_(interaction.locale, "moderation.massban.overview_description"))
        await interaction.response.defer()
        await interaction.edit_original_message(embed=embed, view=self._view)


class MemberView(ui.View):
    MEMBERS_PER_PAGE = 50

    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__()

        self.members = view.members
        self.current_index = 0
        self._view = view

        if len(view.members) < self.MEMBERS_PER_PAGE:
            self.add_item(NextMemberButton(self, locale, disabled=True))
        else:
            self.add_item(NextMemberButton(self, locale))

        self.add_item(BackMemberButton(self, locale, disabled=True))
        self.add_item(CloseMemberViewButton(view, locale))


class MassbanView(ui.View):
    members: list[discord.Member]
    reason: str

    def __init__(self, members: list[discord.Member], reason: str, locale: discord.Locale):
        super().__init__()

        self.members = members
        self.reason = reason

        self.add_item(BanButton(self, locale))
        self.add_item(CancelButton(self, locale))
        self.add_item(ViewMemberButton(self, locale))


@app_commands.guild_only
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
class Massban(app_commands.Group):
    def __init__(self):
        super().__init__(name="massban", description="Bans mutilple users specified by mutiple criteria.")

    @app_commands.command(name="ban", description="Bans users based on a message search.")
    @app_commands.describe(
        channel="The channel to search through. If not specified, the current channel is used.",
        amount="The amount of messages to search through (100).",
        reason="The reason for the massban.",
        message_contains="Must be contained in a message [needs channel].",
        message_starts="Must be at the start of a message [needs channel].",
        message_ends="Must be at the end of a message [needs channel].",
        has_embed="If the message contains an embed [needs channel].",
        has_attachment="If the message contains a attachment [needs channel].",
        joined_after="Only users that joined after this.",
        joined_before="Only users that joined before this.",
        has_role="If users have a role or not.",
        has_avatar="If users have an avatar or not.",
        username_regex="Regex that must be matched in the username.",
        sent_after="Only messages sent after this (id) [needs channel].",
        sent_before="Only messages sent before this (id)  [needs channel].",
        account_younger_days="Only users that are younger than this (days).",
        joined_before_days="Only users that joined before this (days).",
    )
    @app_commands.guild_only
    @app_commands.checks.bot_has_permissions(read_messages=True)
    async def massban(
        self,
        interaction: discord.Interaction,
        reason: app_commands.Range[str, 1, 512],
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.Thread] = None,
        has_avatar: Optional[bool] = None,
        has_role: Optional[bool] = None,
        joined_after: Optional[discord.Member] = None,
        joined_before: Optional[discord.Member] = None,
        username_regex: app_commands.Range[str, 4, 50] = None,
        amount: app_commands.Range[int, 10, 512] = 100,
        message_contains: app_commands.Range[str, 3, 50] = None,
        message_starts: app_commands.Range[str, 3, 50] = None,
        message_ends: app_commands.Range[str, 3, 50] = None,
        has_embed: Optional[bool] = None,
        has_attachment: Optional[bool] = None,
        sent_after: Optional[str] = None,
        sent_before: Optional[str] = None,
        account_younger_days: app_commands.Range[int, 0, 30] = None,
        joined_before_days: app_commands.Range[int, 0, 30] = None,
    ):
        lc = interaction.locale
        await interaction.response.defer(ephemeral=True)

        members = []

        if channel is not None:
            before = sent_before and discord.Object(id=sent_before)
            after = sent_after and discord.Object(id=sent_after)
            predicates = []
            if message_contains:
                predicates.append(lambda m: message_contains in m.content)
            elif message_starts:
                predicates.append(lambda m: m.content.startswith(message_starts))
            elif message_ends:
                predicates.append(lambda m: m.content.endswith(message_ends))

            if has_embed is not None:
                if has_embed:
                    predicates.append(lambda m: len(m.embeds))
                else:
                    predicates.append(lambda m: not len(m.embeds))

            if has_attachment is not None:
                if has_attachment:
                    predicates.append(lambda m: len(m.attachments))
                else:
                    predicates.append(lambda m: not len(m.attachments))

            async for message in channel.history(limit=amount, before=before, after=after):
                if all(p(message) for p in predicates):
                    members.append(message.author)
        else:
            if not interaction.guild.chunked:
                await interaction.guild.chunk(cache=True)

            members = interaction.guild.members

        # member filters
        predicates = [
            lambda m: m.id != interaction.user.id,
            lambda m: can_execute_action(interaction, interaction.user, m),  # Only if applicable
            lambda m: not m.bot,  # No bots
            lambda m: m.discriminator != "0000",  # No deleted users
        ]

        if username_regex:
            try:
                _regex = re.compile(username_regex)
            except re.error as e:
                await interaction.followup.send(_(lc, "moderation.massban.invalid_regex") + f"\n```{e}```")
                return
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if has_avatar is not None:
            if has_avatar:
                predicates.append(lambda m: m.avatar is not None)
            else:
                predicates.append(lambda m: m.avatar is None)

        if has_role is not None:
            if has_role:
                predicates.append(lambda m: len(m._roles) > 0)
            predicates.append(lambda m: len(getattr(m, "roles", [])) <= 1)

        now = discord.utils.utcnow()
        if account_younger_days:

            def created(_member: discord.Member):
                return _member.created_at > now - datetime.timedelta(days=account_younger_days)

            predicates.append(created)

        if joined_before_days:

            def joined(_member: discord.Member):
                if isinstance(_member, discord.User):
                    return True
                return _member.joined_at and _member.joined_at > now - datetime.timedelta(days=joined_before_days)

            predicates.append(joined)

        if joined_after:

            def joined_after(_member, _other=joined_after):
                return _member.joined_at and _other.joined_at and _member.joined_at > _other.joined_at

            predicates.append(joined_after)

        if joined_before:

            def joined_before(_member, _other=joined_before):
                return _member.joined_at and _other.joined_at and _member.joined_at < _other.joined_at

            predicates.append(joined_before)

        members = {m for m in members if all(p(m) for p in predicates)}
        if len(members) == 0:
            await interaction.followup.send(_(lc, "moderation.massban.no_users_found"))
            return

        embed = Embed(description=_(lc, "moderation.massban.overview_description"))
        await interaction.followup.send(embed=embed, view=MassbanView(list(members), reason, interaction.locale))
