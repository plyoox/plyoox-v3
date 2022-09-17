from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from lib import parsers, extensions
from lib.enums import TimerType
from translation import _
from . import _views, _logging_helper, clear_group, automod

if TYPE_CHECKING:
    from main import Plyoox


_T = app_commands.locale_str
DISCORD_INVITE_SINGLE = re.compile(
    r"^(https?://)?discord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})$", re.IGNORECASE
)
DISCORD_INVITE_MULTI = re.compile(
    r"\b(https?://)?discord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b", re.IGNORECASE
)


def can_execute_action(interaction: discord.Interaction, user: discord.Member, target: discord.Member):
    return user == interaction.guild.owner or user.top_role > target.top_role


class Moderation(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

        self.ctx_menu = app_commands.ContextMenu(
            name=_T("Invite info", key="view-invite-info"),
            callback=self.invite_info_context_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    clear_group = clear_group.ClearGroup()
    warn_group = app_commands.Group(
        name="warn",
        description="Commands to manage warnings on a user.",
        guild_only=True,
        default_permissions=discord.Permissions(manage_messages=True),
    )

    @staticmethod
    async def _can_execute_on(interaction: discord.Interaction, target: discord.Member) -> bool:
        if interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.hierarchy_not_permitted"), ephemeral=True
            )
            return False

        if target.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.bot_cannot_punish"), ephemeral=True
            )
            return False

        return True

    @staticmethod
    async def _view_invite_info(interaction: discord.Interaction, *, invite: discord.Invite, ephemeral: bool = False):
        lc = interaction.locale

        embed = extensions.Embed(
            description=_(lc, "moderation.invite_info.description", code=invite.code),
            title=_(lc, "moderation.invite_info.title"),
        )
        embed.set_thumbnail(url=invite.guild.icon)

        embed.add_field(
            name=_(lc, "moderation.invite_info.info"),
            value=f"> __{_(lc, 'moderation.invite_info.url')}:__ {invite.url}\n"
            f"> __{_(lc, 'moderation.invite_info.uses')}:__ {invite.uses or 0}/{invite.max_uses or '∞'}\n"
            f"> __{_(lc, 'created_at')}:__ {discord.utils.format_dt(invite.created_at) if invite.created_at else _(lc, 'moderation.invite_info.no_date')}\n"
            f"> __{_(lc, 'moderation.invite_info.expires_at')}:__ {discord.utils.format_dt(invite.expires_at) if invite.expires_at else _(lc, 'moderation.invite_info.no_date')}",
        )

        if invite.inviter is not None:
            embed.add_field(
                name=_(lc, "moderation.invite_info.creator"),
                value=f"> __{_(lc, 'id')}:__ {invite.inviter.id}\n"
                f"> __{_(lc, 'name')}:__ {invite.inviter}\n"
                f"> __{_(lc, 'moderation.invite_info.mention')}:__{invite.inviter.mention}",
            )
        else:
            embed.add_field(
                name=_(lc, "moderation.invite_info.creator"),
                value=_(lc, "moderation.invite_info.no_creator"),
            )

        embed.add_field(
            name=_(lc, "guild"),
            value=f"> __{_(lc, 'name')}:__ {invite.guild.name}\n"
            f"> __{_(lc, 'id')}:__ {invite.guild.id}\n"
            f"> __{_(lc, 'guild_info.about.vanity_url')}:__ {invite.guild.vanity_url or _(lc, 'guild_info.about.no_vanity_url')}\n"
            f"> __{_(lc, 'moderation.invite_info.member_count')}:__ {invite.approximate_member_count}",
        )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(name="ban", description="Bans an user from the guild.")
    @app_commands.describe(member="The member that should be banned.", reason="Why the member should be banned.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="ban")
        await guild.ban(member, reason=reason, delete_message_days=1)
        await interaction.followup.send(_(lc, "moderation.ban.successfully_banned"), ephemeral=True)

    @app_commands.command(name="tempban", description="Bans an user from the guild for a specific time.")
    @app_commands.describe(
        member=_T("The member that should be banned.", key="ban.member"),
        reason=_T("Why the member should be banned.", key="ban.reason"),
        duration="How long the member should be banned.",
    )
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def tempban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        banned_until = parsers.parse_datetime_from_string(duration)
        if banned_until is None:
            await interaction.response.send_message(_(lc, "moderation.invalid_duration"), ephemeral=True)
            return

        if (banned_until - discord.utils.utcnow()).total_seconds() > 31_536_000:
            await interaction.response.send_message(_(lc, "moderation.tempban.too_long"), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=banned_until, reason=reason, type="tempban"
        )
        await self.bot.timer.create_timer(member.id, guild.id, type=TimerType.tempban, expires=banned_until)
        await guild.ban(member, reason=reason, delete_message_days=1)

        await interaction.followup.send(_(lc, "moderation.tempban.successfully_banned"), ephemeral=True)

    @app_commands.command(name="kick", description="Kicks an user from the guild.")
    @app_commands.describe(member="The member that should be kicked.", reason="Why the member should be kicked.")
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.followup.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="kick")
        await guild.kick(member, reason=reason)

        await interaction.followup.send(_(lc, "moderation.kick.successfully_kicked"), ephemeral=True)

    @app_commands.command(name="tempmute", description="Mutes an user for a specific time.")
    @app_commands.describe(
        member="The member that should be muted.",
        reason="Why the member should be muted.",
        duration="How long the member should be muted (max 28 days).",
    )
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def tempmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale

        banned_until = parsers.parse_datetime_from_string(duration)
        if banned_until is None:
            await interaction.response.send_message(_(lc, "moderation.invalid_duration"), ephemeral=True)
            return

        if (banned_until - discord.utils.utcnow()).total_seconds() > 86400 * 28:
            await interaction.response.send_message(_(lc, "moderation.tempmute.too_long"), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)
        await member.timeout(banned_until, reason=reason)
        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=banned_until, reason=reason, type="tempmute"
        )

        await interaction.followup.send(_(lc, "moderation.tempmute.successfully_muted"), ephemeral=True)

    @app_commands.command(name="unban", description="Unbans an user from the guild.")
    @app_commands.describe(user="The member that should be unbanned.", reason="Why the member has been unbanned.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def unban(
        self, interaction: discord.Interaction, user: discord.User, reason: Optional[app_commands.Range[str, None, 512]]
    ):
        lc = interaction.locale
        guild = interaction.guild

        try:
            await guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message(_(lc, "moderation.unban.not_banned"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(interaction, target=user, reason=reason, type="unban")

        await self.bot.db.execute(
            "DELETE FROM timers WHERE target_id = $1 AND guild_id = $2 AND type = 'tempban'", user.id, guild.id
        )

        await interaction.followup.send(_(lc, "moderation.unban.successfully_unbanned"), ephemeral=True)

    @app_commands.command(name="softban", description="Kicks an user from the guild and deletes their messages.")
    @app_commands.describe(
        member=_T("The member that should be kicked.", key="kick.member"),
        reason=_T("Why the member should be kicked.", key="kick.reason"),
    )
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def softban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="softban")
        await guild.ban(member, reason=reason, delete_message_days=1)
        await guild.unban(member, reason=reason)

        await interaction.followup.send(_(lc, "moderation.softban.successfully_kicked"), ephemeral=True)

    @app_commands.command(name="slowmode", description="Sets the slowmode of the current channel.")
    @app_commands.describe(duration="How long the slowmode should be (max 6hrs).")
    @app_commands.checks.cooldown(2, 10, key=lambda i: i.channel_id)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def slowmode(self, interaction: discord.Interaction, duration: Optional[app_commands.Range[int, 1, 21600]]):
        lc = interaction.locale

        if duration is None:
            await interaction.channel.edit(slowmode_delay=0)
            await interaction.response.send_message(_(lc, "moderation.slowmode.disabled"), ephemeral=True)
        else:
            await interaction.channel.edit(slowmode_delay=duration)
            await interaction.response.send_message(_(lc, "moderation.slowmode.enabled"), ephemeral=True)

    @app_commands.command(name="unmute", description="Unmutes an user.")
    @app_commands.describe(member="The member that should be unmuted.", reason="Why the member should be unmuted.")
    @app_commands.checks.bot_has_permissions(mute_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await member.timeout(None, reason=_(lc, "moderation.unmute.reason"))
        await _logging_helper.log_simple_punish_command(interaction, target=member, type="unmute", reason=reason)

        await interaction.followup.send(_(lc, "moderation.unmute.successfully_unmuted"), ephemeral=True)

    @app_commands.command(name="invite-info", description="Shows information about a invite.")
    @app_commands.describe(invite="The invite you want to get information about.")
    @app_commands.checks.cooldown(2, 30, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def invite_info(self, interaction: discord.Interaction, invite: str):
        lc = interaction.locale

        if not DISCORD_INVITE_SINGLE.match(invite):
            await interaction.response.send_message(_(lc, "moderation.invite_info.invalid_invite"), ephemeral=True)
            return

        invite = await self.bot.fetch_invite(invite, with_counts=True, with_expiration=True)
        if invite is None:
            await interaction.response.send_message(_(lc, "moderation.invite_info.not_found"), ephemeral=True)
            return

        await self._view_invite_info(interaction, invite=invite)

    @app_commands.guild_only
    @app_commands.default_permissions(manage_messages=True)
    async def invite_info_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        lc = interaction.locale

        invites = DISCORD_INVITE_MULTI.findall(message.content)

        if not invites:
            await interaction.response.send_message(
                _(lc, "moderation.invite_info.invalid_invite_message"), ephemeral=True
            )
            return

        invite = await self.bot.fetch_invite(invites[0][-1], with_expiration=True, with_counts=True)
        if invite is None:
            await interaction.response.send_message(_(lc, "moderation.invite_info.not_found"), ephemeral=True)
            return

        await self._view_invite_info(interaction, invite=invite, ephemeral=True)

    @app_commands.command(name="massban", description="Bans users based on a multiple factors.")
    @app_commands.describe(
        channel="The channel to search through. If not specified, the current channel is used.",
        amount="The amount of messages to search through (100).",
        reason="The reason for the massban.",
        message_contains="Must be contained in a message.",
        message_starts="Must be at the start of a message.",
        message_ends="Must be at the end of a message",
        has_embed="If the message contains an embed.",
        has_attachment="If the message contains a attachment.",
        joined_after="Only users that joined after this.",
        joined_before="Only users that joined before this.",
        has_role="If users have a role or not.",
        has_avatar="If users have an avatar or not.",
        username_regex="Regex that must be matched in the username.",
        sent_after="Only messages sent after this (id).",
        sent_before="Only messages sent before this (id).",
        account_younger_days="Only users that are younger than this (days).",
        joined_before_days="Only users that joined before this (days).",
    )
    @app_commands.guild_only
    @app_commands.checks.bot_has_permissions(read_messages=True)
    @app_commands.default_permissions(administrator=True)
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

        embed = extensions.Embed(description=_(lc, "moderation.massban.overview_description"))
        await interaction.followup.send(embed=embed, view=_views.MassbanView(interaction, list(members), reason))

    @warn_group.command(name="list", description="Lists current warnings for a user.")
    @app_commands.describe(member="The user to list warnings for.")
    async def warn_list(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        if member.bot:
            await interaction.response.send_message(_(lc, "moderation.warn.no_bots"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        warnings = await self.bot.db.fetch(
            "SELECT id, points, reason, timestamp FROM automod_users WHERE user_id = $1 AND guild_id = $2",
            member.id,
            interaction.guild_id,
        )

        if not warnings:
            await interaction.followup.send(_(lc, "moderation.warn.no_warnings"), ephemeral=True)
            return

        embed = extensions.Embed(title=_(lc, "moderation.warn.list_title"))
        embed.description = ""

        for warning in warnings:
            embed.description += f"`{warning['id']}`. {warning['points']} {_(lc, f'moderation.warn.point' + ('s' if warning['points'] != 1 else ''))} - {warning['reason']} - {discord.utils.format_dt(warning['timestamp'])}\n"

        await interaction.followup.send(embed=embed, ephemeral=True)

    @warn_group.command(name="add", description="Adds a warning to a user.")
    @app_commands.describe(
        member="The user to add a warning to.",
        points="The amount of points to add.",
        reason="The reason for the warning.",
    )
    async def warn_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        points: app_commands.Range[int, 1, 20],
        reason: app_commands.Range[str, 1, 128],
    ):
        lc = interaction.locale
        if member.bot:
            await interaction.response.send_message(_(lc, "moderation.warn.no_bots"), ephemeral=True)
            return

        automod_cog: automod.Automod | None = self.bot.get_cog("Automod")
        if automod_cog is None:
            await interaction.followup.send(_(interaction.locale, "moderation.warn.automod_not_loaded"), ephemeral=True)
            return

        if not await self._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        cache = await self.bot.cache.get_moderation(interaction.guild_id)
        if cache is None:
            await interaction.followup.send(_(lc, "moderation.warn.no_settings"), ephemeral=True)
            return

        if not cache.active:
            await interaction.followup.send(_(lc, "moderation.warn.disabled"), ephemeral=True)
            return

        if not cache.automod_actions:
            await interaction.followup.send(_(lc, "moderation.warn.no_actions"), ephemeral=True)
            return

        await automod_cog.add_warn_points(member, interaction.user, points, reason)

        await interaction.followup.send(_(lc, "moderation.warn.success"))

    @warn_group.command(name="remove", description="Removes a warning from a user.")
    @app_commands.describe(member="The user to remove a warning from.", id="The ID of the warning to remove.")
    async def warn_remove(
        self, interaction: discord.Interaction, member: discord.Member, id: app_commands.Range[int, 0]
    ):
        lc = interaction.locale
        if member.bot:
            await interaction.response.send_message(_(lc, "moderation.warn.no_bots"), ephemeral=True)
            return

        query_response = await self.bot.db.execute(
            "DELETE FROM automod_users WHERE id = $1 and guild_id = $2 AND user_id = $3",
            id,
            interaction.guild_id,
            member.id,
        )

        if query_response == "DELETE 1":
            await interaction.response.send_message(_(lc, "moderation.warn.successfully_removed"), ephemeral=True)
        else:
            await interaction.followup.send_message(_(lc, "moderation.warn.not_found"), ephemeral=True)

    @warn_group.command(name="remove-all", description="Removes all warnings from a user.")
    @app_commands.describe(member="The user to remove all warnings from.")
    async def warn_remove_all(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        if member.bot:
            await interaction.response.send_message(_(lc, "moderation.warn.no_bots"), ephemeral=True)
            return

        query_response = await self.bot.db.execute(
            "DELETE FROM automod_users WHERE guild_id = $2 AND user_id = $3",
            interaction.guild_id,
            member.id,
        )

        if int(query_response.split(" ")[1]) >= 1:
            await interaction.response.send_message(_(lc, "moderation.warn.successfully_removed_all"), ephemeral=True)
        else:
            await interaction.response.send_message(_(lc, "moderation.warn.no_warnings_found"), ephemeral=True)

    @tempmute.autocomplete("duration")
    @tempban.autocomplete("duration")
    async def autocomplete_duration(self, interaction: discord.Interaction, current: str):
        lc = interaction.locale

        times = [
            {"label": f"30 {_(lc, 'times.minutes')}", "value": "30min"},
            {"label": f"1 {_(lc, 'times.hour')}", "value": "1h"},
            {"label": f"3 {_(lc, 'times.hours')}", "value": "3h"},
            {"label": f"6 {_(lc, 'times.hours')}", "value": "6h"},
            {"label": f"12 {_(lc, 'times.hours')}", "value": "12h"},
            {"label": f"1 {_(lc, 'times.day')}", "value": "1d"},
            {"label": f"3 {_(lc, 'times.days')}", "value": "3d"},
            {"label": f"7 {_(lc, 'times.days')}", "value": "7d"},
            {"label": f"14 {_(lc, 'times.days')}", "value": "14d"},
            {"label": f"1 {_(lc, 'times.month')} (28 {_(lc, 'times.days')})", "value": "28d"},
        ]

        if not current:
            return [app_commands.Choice(name=time["label"], value=time["value"]) for time in times]

        return [
            app_commands.Choice(name=time["label"], value=time["value"])
            for time in times
            if current.lower() in time["label"].lower()
        ]
