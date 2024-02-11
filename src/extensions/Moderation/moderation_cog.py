from __future__ import annotations

import datetime
import logging
import re
from typing import TYPE_CHECKING, Optional, Union

import discord
from discord import app_commands, utils
from discord.ext import commands
from discord.app_commands import locale_str as _

from cache import Punishment
from lib import parsers, extensions
from lib.enums import TimerEnum, ModerationCommandKind
from . import _views as views, _logging_helper, clear_group, automod
from .automod import Automod, AutoModerationActionData

if TYPE_CHECKING:
    from main import Plyoox

_log = logging.getLogger(__name__)


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
            name=_("Invite info"),
            callback=self.invite_info_context_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    clear_group = clear_group.ClearGroup()
    warn_group = app_commands.Group(
        name="warn",
        description=_("Commands to manage warnings on a user."),
        guild_only=True,
        default_permissions=discord.Permissions(manage_messages=True),
    )

    @staticmethod
    async def _can_execute_on(interaction: discord.Interaction, target: discord.Member) -> bool:
        if interaction.user.top_role <= target.top_role or interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_translated(
                _("The user must be below you in the hierarchy."), ephemeral=True
            )
            return False

        if target.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_translated(
                _("The user must be below the bot in the hierarchy."), ephemeral=True
            )
            return False

        if target.guild_permissions.administrator:
            await interaction.response.send_translated(_("You cannot punish administrators."), ephemeral=True)
            return False

        if target.bot:
            await interaction.response.send_translated(_("You cannot punish bots."), ephemeral=True)
            return False

        return True

    @staticmethod
    async def _view_invite_info(interaction: discord.Interaction, *, invite: discord.Invite, ephemeral: bool = False):
        embed = extensions.Embed(
            description=interaction.translate(_("Information about the invite `{invite}`")).format(invite=invite.code),
            title=interaction.translate(_("Invite information")),
        )
        embed.set_thumbnail(url=invite.guild.icon)

        created_at = (
            discord.utils.format_dt(invite.created_at) if invite.created_at else interaction.translate(_("No date"))
        )
        expires_at = (
            discord.utils.format_dt(invite.expires_at) if invite.expires_at else interaction.translate(_("No date"))
        )
        embed.add_field(
            name=interaction.translate(_("Information")),
            value=f"> __{interaction.translate(_('Url'))}:__ {invite.url}\n"
            f"> __{interaction.translate(_('Uses'))}:__ {invite.uses or 0}/{invite.max_uses or '∞'}\n"
            f"> __{interaction.translate(_('Created at'))}:__ {created_at}\n"
            f"> __{interaction.translate(_('Expires at'))}:__ {expires_at}",
        )

        if invite.inviter is not None:
            value = (
                f"> __{interaction.translate(_('Id'))}:__ {invite.inviter.id}\n"
                f"> __{interaction.translate(_('Name'))}:__ {invite.inviter}\n"
                f"> __{interaction.translate(_('Mention'))}:__{invite.inviter.mention}",
            )
        else:
            value = interaction.translate(_("No creator"))
        embed.add_field(
            name=interaction.translate(_("Creator")),
            value=value,
        )

        embed.add_field(
            name=interaction.translate(_("Guild")),
            value=f"> __{interaction.translate(_('Name'))}:__ {invite.guild.name}\n"
            f"> __{interaction.translate(_('Id'))}:__ {invite.guild.id}\n"
            f"> __{interaction.translate('Vanity Url')}:__ {invite.guild.vanity_url or interaction.translate(_('No vanity url'))}\n"
            f"> __{interaction.translate('Member count')}:__ {invite.approximate_member_count}",
        )

        await interaction.response.send_message(embeds=[embed], ephemeral=ephemeral)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self.bot.db.execute(
            "DELETE FROM timer WHERE target_id = $1 AND guild_id = $2 AND kind = 'temp_ban'", user.id, guild.id
        )

    @app_commands.command(name="ban", description=_("Bans an user from the guild."))
    @app_commands.describe(member=_("The member that should be banned."), reason=_("Why the member should be banned."))
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def ban(
        self,
        interaction: discord.Interaction,
        member: Union[discord.Member, discord.User],
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        guild = interaction.guild

        if isinstance(member, discord.Member) and not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(
            interaction, target=member, reason=reason, kind=ModerationCommandKind.ban
        )
        await guild.ban(member, reason=reason, delete_message_days=1)
        await interaction.followup.send(
            interaction.translate(_("The user has been permanently banned.")), ephemeral=True
        )

    @app_commands.command(name="tempban", description=_("Bans an user from the guild for a specific time."))
    @app_commands.describe(
        member=_("The member that should be banned."),
        reason=_("Why the member should be banned."),
        duration=_("How long the member should be banned."),
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
        guild = interaction.guild

        banned_until = parsers.parse_datetime_from_string(duration)
        if banned_until is None:
            await interaction.response.send_translated(_("The provided duration is invalid."), ephemeral=True)
            return

        ban_duration = (banned_until - discord.utils.utcnow()).total_seconds()
        if ban_duration > 31_536_000:  # 365 days
            await interaction.response.send_translated(_("The provided duration is too long."), ephemeral=True)
            return

        if ban_duration < 60:
            await interaction.response.send_translated(_("The minimum duration is 60 seconds."), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=banned_until, reason=reason, kind=ModerationCommandKind.tempban
        )
        await self.bot.timer.create_timer(member.id, guild.id, kind=TimerEnum.temp_ban, expires=banned_until)
        await guild.ban(member, reason=reason, delete_message_days=1)

        await interaction.followup.send(
            interaction.translate(_("The user has been banned until {timestamp}.")).format(
                timestamp=utils.format_dt(banned_until)
            ),
            ephemeral=True,
        )

    @app_commands.command(name="kick", description=_("Kicks an user from the guild."))
    @app_commands.describe(member=_("The member that should be kicked."), reason=_("Why the member should be kicked."))
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(
            interaction, target=member, reason=reason, kind=ModerationCommandKind.kick
        )
        await guild.kick(member, reason=reason)

        await interaction.followup.send(interaction.translate(_("The user has been kicked.")), ephemeral=True)

    @app_commands.command(name="tempmute", description=_("Mutes a member for a specific time."))
    @app_commands.describe(
        member=_("The member that should be muted."),
        reason=_("Why the member should be muted."),
        duration=_("How long the member should be muted (max 28 days)."),
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
        muted_until = parsers.parse_datetime_from_string(duration)
        if muted_until is None:
            await interaction.response.send_translated(_("The provided duration is invalid."), ephemeral=True)
            return

        if (muted_until - discord.utils.utcnow()).total_seconds() > 86400 * 28:
            await interaction.response.send_translated(_("The provided duration is too long."), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await member.timeout(muted_until, reason=reason)
        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=muted_until, reason=reason, kind=ModerationCommandKind.tempmute
        )

        await interaction.followup.send(
            interaction.translate(_("The member has been muted until {timestamp}.")).format(
                timestamp=utils.format_dt(muted_until)
            ),
            ephemeral=True,
        )

    @app_commands.command(name="unban", description=_("Unbans an user from the guild."))
    @app_commands.describe(user=_("The user that should be unbanned."), reason=_("Why the user should be unbanned."))
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def unban(
        self, interaction: discord.Interaction, user: discord.User, reason: Optional[app_commands.Range[str, None, 512]]
    ):
        guild = interaction.guild

        try:
            await guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_translated(_("The user is not banned on this server."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(
            interaction, target=user, reason=reason, kind=ModerationCommandKind.unban
        )

        await interaction.followup.send(interaction.translate(_("The user has been unbanned.")), ephemeral=True)

    @app_commands.command(name="softban", description=_("Kicks a member from the guild and deletes their messages."))
    @app_commands.describe(member=_("The member that should be kicked."), reason=_("Why the member should be kicked."))
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def softban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(
            interaction, target=member, reason=reason, kind=ModerationCommandKind.softban
        )
        await guild.ban(member, reason=reason, delete_message_days=1)
        await guild.unban(member, reason=reason)

        await interaction.followup.send(interaction.translate(_("The user has been kicked.")), ephemeral=True)

    @app_commands.command(name="slowmode", description=_("Sets the slowmode of the current channel."))
    @app_commands.describe(duration=_("How long the slowmode should be (max 6hrs)."))
    @app_commands.checks.cooldown(2, 10, key=lambda i: i.channel_id)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def slowmode(self, interaction: discord.Interaction, duration: Optional[app_commands.Range[int, 1, 21600]]):
        if duration is None:
            await interaction.channel.edit(slowmode_delay=0)
            await interaction.response.send_translated(_("The slowmode has been disabled."), ephemeral=True)
        else:
            await interaction.channel.edit(slowmode_delay=duration)
            await interaction.response.send_translated(_("The slowmode has been enabled."), ephemeral=True)

    @app_commands.command(name="unmute", description=_("Unmutes a member."))
    @app_commands.describe(
        member=_("The member that should be unmuted."), reason=_("Why the member should be unmuted.")
    )
    @app_commands.checks.bot_has_permissions(mute_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await member.timeout(None, reason=reason)
        await _logging_helper.log_simple_punish_command(
            interaction, target=member, kind=ModerationCommandKind.unmute, reason=reason
        )

        await interaction.followup.send(interaction.translate(_("The member has been unmuted.")), ephemeral=True)

    @app_commands.command(name="invite-info", description=_("Shows information about a invite."))
    @app_commands.describe(invite=_("The invite you want to get information about."))
    @app_commands.checks.cooldown(2, 30, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def invite_info(self, interaction: discord.Interaction, invite: str):
        if not DISCORD_INVITE_SINGLE.match(invite):
            await interaction.response.send_translated(_("The input is not a valid invite."), ephemeral=True)
            return

        try:
            invite = await self.bot.fetch_invite(invite, with_counts=True, with_expiration=True)
        except discord.NotFound:
            await interaction.response.send_translated(_("The invite does not exist."), ephemeral=True)
            return

        await self._view_invite_info(interaction, invite=invite)

    @app_commands.guild_only
    @app_commands.default_permissions(manage_messages=True)
    async def invite_info_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        invites = DISCORD_INVITE_MULTI.findall(message.content)

        if not invites:
            await interaction.response.send_translated(_("This message does not contain an invite."), ephemeral=True)
            return

        try:
            invite = await self.bot.fetch_invite(invites[0][-1], with_expiration=True, with_counts=True)
        except discord.NotFound:
            await interaction.response.send_translated(_("The invite does not exist."), ephemeral=True)
            return

        await self._view_invite_info(interaction, invite=invite, ephemeral=True)

    @app_commands.command(name="massban", description=_("Bans users based on a multiple factors."))
    @app_commands.describe(
        channel=_("The channel to search through. If not specified, the current channel is used."),
        amount=_("The amount of messages to search through (100)."),
        reason=_("The reason for the massban."),
        message_contains=_("Must be contained in a message."),
        message_starts=_("Must be at the start of a message."),
        message_ends=_("Must be at the end of a message."),
        has_embed=_("If the message contains an embed."),
        has_attachment=_("If the message contains a attachment."),
        joined_after=_("Only users that joined after this."),
        joined_before=_("Only users that joined before this."),
        has_role=_("If users have a role or not."),
        has_avatar=_("If users have an avatar or not."),
        username_regex=_("Regex that must be matched in the username."),
        sent_after=_("Only messages sent after this (id)."),
        sent_before=_("Only messages sent before this (id)."),
        account_younger_days=_("Only users that are younger than this (in days)."),
        joined_before_days=_("Only users that joined before this (in days)."),
    )
    @app_commands.guild_only
    @app_commands.checks.bot_has_permissions(read_messages=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(2, 60, key=lambda i: (i.guild.id, i.user.id))
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
                await interaction.followup.send(
                    interaction.translate(_("The provided regex is invalid.")) + f"\n```{e}```"
                )
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
            await interaction.followup.send(
                interaction.translate(_("There are no users that meets this criteria.")), ephemeral=True
            )
            return

        embed = extensions.Embed(
            description=interaction.translate(_("Confirm the selection of users scheduled for ban."))
        )
        await interaction.followup.send(embed=embed, view=views.MassbanView(interaction, list(members), reason))

    @warn_group.command(name="list", description=_("Lists current warnings for a user."))
    @app_commands.describe(user=_("The user to list warnings for."))
    async def warn_list(self, interaction: discord.Interaction, user: discord.User):
        if user.bot:
            await interaction.response.send_translated(_("Bots cannot be punished."), ephemeral=True)
            return

        warn_view = views.WarnView(interaction, user)

        embed = await warn_view.initialize()
        await interaction.response.send_message(view=warn_view, embed=embed, ephemeral=True)

    @warn_group.command(name="add", description=_("Adds a warning to a user."))
    @app_commands.describe(
        member=_("The user to add a warning to."),
        points=_("The amount of points to add."),
        reason=_("The reason for the warning."),
    )
    async def warn_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        points: app_commands.Range[int, 1, 20],
        reason: app_commands.Range[str, 1, 128],
    ):
        if member.bot:
            await interaction.response.send_translated(_("Bots cannot be punished."), ephemeral=True)
            return

        automod_cog: automod.Automod | None = self.bot.get_cog("Automod")
        if automod_cog is None:
            _log.warning("Automod cog is not loaded.")
            await interaction.response.send_translated(_("The required module is not loaded."), ephemeral=True)
            return

        if not await self._can_execute_on(interaction, member):
            return

        cache = await self.bot.cache.get_moderation(interaction.guild_id)
        if cache is None:
            await interaction.response.send_translated(
                _("This has not been set up. Please visit https://plyoox.net"), ephemeral=True
            )
            return

        if not cache.active:
            await interaction.response.send_translated(
                _("The module is currently disabled. Enabled it on the [Dashboard](https://plyoox.net)."),
                ephemeral=True,
            )
            return

        if not cache.point_actions:
            await interaction.response.send_translated(_("There are no point actions configured."), ephemeral=True)
            return

        await automod_cog.add_warn_points(member, interaction.user, points, reason)

        await interaction.response.send_translated(
            _("{user.mention} has been warned."), ephemeral=True, translation_data={"user": member}
        )

    @warn_group.command(name="remove", description=_("Removes a warning from a user."))
    @app_commands.describe(member=_("The user to remove a warning from."), id=_("The ID of the warning to remove."))
    async def warn_remove(self, interaction: discord.Interaction, member: discord.User, id: app_commands.Range[int, 0]):
        if member.bot:
            await interaction.response.send_translated(_("Bots cannot be punished."), ephemeral=True)
            return

        query_response = await self.bot.db.execute(
            "DELETE FROM automoderation_user WHERE id = $1 and guild_id = $2 AND user_id = $3",
            id,
            interaction.guild_id,
            member.id,
        )

        if query_response == "DELETE 1":
            await interaction.response.send_translated(_("The warning has been removed."), ephemeral=True)
        else:
            await interaction.response.send_translated(
                _("There is no warning with the id `{id}`"),
                ephemeral=True,
                translation_data={"id": id},
            )

    @warn_group.command(name="remove-all", description=_("Removes all warnings from a user."))
    @app_commands.describe(member=_("The user to remove all warnings from."))
    async def warn_remove_all(self, interaction: discord.Interaction, member: discord.User):
        if member.bot:
            await interaction.response.send_translated(_("Bots cannot be punished."), ephemeral=True)
            return

        query_response = await self.bot.db.execute(
            "DELETE FROM automoderation_user WHERE guild_id = $1 AND user_id = $2",
            interaction.guild_id,
            member.id,
        )

        if int(query_response.split(" ")[1]) >= 1:
            await interaction.response.send_translated(_("All warnings have been removed."), ephemeral=True)
        else:
            await interaction.response.send_translated(
                _("{member} has no warnings"), ephemeral=True, translation_data={"member": str(member)}
            )

    @app_commands.command(name="punish", description=_("Punish a user with predefined templates."))
    @app_commands.describe(member=_("The user to punish."))
    @app_commands.default_permissions(ban_members=True)
    async def punish(self, interaction: discord.Interaction, member: discord.Member, template: int):
        automod: Automod = self.bot.get_cog("Automod")  # type: ignore
        if automod is None:
            _log.warning("Automod cog is not loaded.")
            await interaction.response.send_translated(_("The required module is not loaded."), ephemeral=True)
            return

        cache = await self.bot.cache.get_punishments(interaction.guild_id)
        if cache is None:
            await interaction.response.send_translated(_("There are no punishments configured."), ephemeral=True)
            return

        punishment = cache.get(template)
        if punishment is None:
            await interaction.response.send_translated(_("The provided template does not exist."), ephemeral=True)
            return

        if not await self._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        for action in punishment.actions:
            if automod._handle_checks(member, action):
                data = AutoModerationActionData(
                    action=action, member=member, reason=punishment.reason, moderator=interaction.user
                )

                await automod._execute_action(data)

        await interaction.followup.send(interaction.translate(_("The user has been punished.")), ephemeral=True)

    @tempmute.autocomplete("duration")
    @tempban.autocomplete("duration")
    async def autocomplete_duration(self, interaction: discord.Interaction, current: str):
        times = [
            {"label": f"5 {interaction.translate(_('minutes'))}", "value": "5min"},
            {"label": f"10 {interaction.translate(_('minutes'))}", "value": "10min"},
            {"label": f"15 {interaction.translate(_('minutes'))}", "value": "15min"},
            {"label": f"30 {interaction.translate(_('minutes'))}", "value": "30min"},
            {"label": f"1 {interaction.translate(_('hours'))}", "value": "1h"},
            {"label": f"3 {interaction.translate(_('hours'))}", "value": "3h"},
            {"label": f"6 {interaction.translate(_('hours'))}", "value": "6h"},
            {"label": f"12 {interaction.translate(_('hours'))}", "value": "12h"},
            {"label": f"1 {interaction.translate(_('day'))}", "value": "1d"},
            {"label": f"3 {interaction.translate(_('days'))}", "value": "3d"},
            {"label": f"7 {interaction.translate(_('days'))}", "value": "7d"},
            {"label": f"14 {interaction.translate(_('days'))}", "value": "14d"},
            {"label": f"1 {interaction.translate(_('month'))} (28 {interaction.translate(_('days'))})", "value": "28d"},
        ]

        if not current:
            return [app_commands.Choice(name=time["label"], value=time["value"]) for time in times]

        return [
            app_commands.Choice(name=time["label"], value=time["value"])
            for time in times
            if current.lower() in time["label"].lower()
        ]

    @punish.autocomplete("template")
    async def autocomplete_template(self, interaction: discord.Interaction, search: str):
        def sort(value: Punishment):
            return search in value.name.lower()

        cache = await self.bot.cache.get_punishments(interaction.guild_id)
        if cache is None:
            return []

        punishment_list = list(cache.values())

        if len(punishment_list) <= 25:
            return [app_commands.Choice(name=value.name, value=value.id) for value in punishment_list]

        punishment_list.sort(key=sort)
        return [app_commands.Choice(name=value.name, value=value.id) for value in punishment_list[:25]]
