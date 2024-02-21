from __future__ import annotations

import asyncio
import datetime
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord.app_commands import locale_str as _
from discord.ext import commands

from cache.models import ModerationModel, AutoModerationAction, ModerationPoints
from lib import utils
from lib.enums import (
    AutoModerationPunishmentKind,
    AutoModerationCheckKind,
    TimerEnum,
    AutomodFinalActionEnum,
    AutoModerationExecutionKind,
)
from translation import translate as global_translate
from . import _logging_helper as _logging

if TYPE_CHECKING:
    from main import Plyoox

_log = logging.getLogger(__name__)

DISCORD_INVITE = re.compile(r"\bdiscord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b", re.IGNORECASE)
EVERYONE_MENTION = re.compile("@(here|everyone)")
LINK_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", re.IGNORECASE)


class AutoModerationActionData(object):
    member: discord.Member
    trigger_content: str | None
    trigger_reason: str
    trigger_action: AutoModerationAction
    moderator: discord.Member | None

    __slots__ = ("trigger_content", "member", "trigger_reason", "trigger_action", "moderator")

    def __init__(
        self,
        member: discord.Member,
        reason: str,
        action: AutoModerationAction,
        content: str | None = None,
        moderator: discord.Member | None = None,
    ):
        self.member = member
        self.trigger_action = action
        self.trigger_content = content
        self.trigger_reason = reason
        self.moderator = moderator

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} member={self.member} trigger_action={self.trigger_action!r} trigger_content={self.trigger_content!r} trigger_reason={self.trigger_reason!r} moderator={self.moderator!r}>"

    @classmethod
    def _from_message(
        cls,
        *,
        bot: Plyoox,
        message: discord.Message,
        action_taken: AutoModerationAction,
        reason: AutoModerationExecutionKind,
    ):
        translated_reason = cls._translate_reason(bot, reason, message.guild.preferred_locale)

        return cls(member=message.author, action=action_taken, content=message.content, reason=translated_reason)

    @property
    def guild(self):
        return self.member.guild

    @staticmethod
    def _translate_reason(bot: Plyoox, reason: AutoModerationExecutionKind, locale: discord.Locale) -> str:
        if reason == "invite":
            return global_translate(_("Discord invite"), bot, locale)
        elif reason == "link":
            return global_translate(_("External link"), bot, locale)
        elif reason == "caps":
            return global_translate(_("Caps spam"), bot, locale)
        elif reason == "point":
            return global_translate(_("Maximum number of points reached"), bot, locale)
        elif reason == "discord_rule":
            return global_translate(_("Violating a Discord moderation rule"), bot, locale)


class Automod(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self.invite_cache: dict[str, discord.Invite | None] = utils.ExpiringCache(seconds=600)
        self.punished_members: dict[tuple[int, int], bool] = utils.ExpiringCache(seconds=3)
        self._invite_requests: dict[str, asyncio.Event] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._run_automod(message)

    @commands.Cog.listener()
    async def on_custom_message_edit(self, before: discord.Message, after: discord.Message):
        if after.content and after.content != before.content:
            await self._run_automod(after)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule) -> None:
        await self.bot.db.execute("DELETE FROM automoderation_rule WHERE rule_id = $1", rule.id)

        self.bot.cache.remove_cache(rule.id, "automod")

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        guild = execution.guild

        # Only accept block message actions
        if execution.action.type != discord.AutoModRuleActionType.block_message:
            return

        # Currently only support keyword rules and the mention spam rule
        if (
            execution.rule_trigger_type != discord.AutoModRuleTriggerType.keyword
            and execution.rule_trigger_type != discord.AutoModRuleTriggerType.mention_spam
        ):
            return

        moderation_cache = await self.bot.cache.get_moderation(guild.id)
        if not moderation_cache or not moderation_cache.active:
            return

        cache = await self.bot.cache.get_moderation_rule(execution.rule_id)
        if not cache:  # Not configured or no actions
            return

        if not guild.chunked:
            await guild.chunk()

        member = execution.member
        if member is None:
            _log.warning(f"Member {execution.user_id} not found in guild {guild.id}")
            return

        for action in cache.actions:
            if Automod._handle_checks(member, action):
                reason = cache.reason or global_translate(
                    _("Violating a Discord moderation rule"), self.bot, guild.preferred_locale
                )

                await self._execute_action(
                    data=AutoModerationActionData(
                        action=action,
                        member=member,
                        reason=reason,
                        content=execution.matched_content,
                    )
                )
                return

    async def _run_automod(self, message: discord.Message):
        guild = message.guild
        author = message.author

        if author.bot:
            return

        if isinstance(author, discord.User):
            return

        if author.guild_permissions.administrator:
            return

        cache = await self.bot.cache.get_moderation(guild.id)
        if cache is None or not cache.active:
            return

        if found_invites := DISCORD_INVITE.findall(message.content):
            if not self._is_affected(message, cache, AutoModerationExecutionKind.invite):
                return

            invites: set[str] = set([invite[1] for invite in found_invites])
            for invite in invites:
                try:
                    fetched_invite = await self._fetch_invite(invite)

                    if fetched_invite and (
                        fetched_invite.guild.id == guild.id or fetched_invite.guild.id in cache.invite_exempt_guilds
                    ):
                        continue

                    await self._handle_action(message, cache.invite_actions, AutoModerationExecutionKind.invite)
                    return
                except discord.HTTPException:
                    break

        if found_links := LINK_REGEX.findall(message.content):
            if not self._is_affected(message, cache, AutoModerationExecutionKind.link):
                return

            links = set([link for link in found_links])
            for link in links:
                if link in ["discord.gg", "discord.com"]:
                    continue

                if cache.link_is_whitelist:
                    if link in cache.link_list:
                        continue
                else:
                    if link not in cache.link_list:
                        continue

                await self._handle_action(message, cache.link_actions, AutoModerationExecutionKind.link)
                return

        if len(message.content) > 15 and not message.content.islower():
            len_caps = len(re.findall(r"[A-ZÄÖÜ]", message.content))
            percent = len_caps / len(message.content)

            # Only check for messages with more than 70% capital letters
            if percent < 0.7:
                return

            if not self._is_affected(message, cache, AutoModerationExecutionKind.caps):
                return

            await self._handle_action(message, cache.caps_actions, AutoModerationExecutionKind.caps)
            return

    async def _fetch_invite(self, code: str) -> discord.Invite | None:
        if (invite := self.invite_cache.get(code, False)) is not False:
            return invite

        if (request := self._invite_requests.get(code)) is not None:
            await request.wait()
            return self.invite_cache[code]

        self._invite_requests[code] = event = asyncio.Event()

        invite = None
        try:
            invite = await self.bot.fetch_invite(code, with_counts=False, with_expiration=False)
            self.invite_cache[code] = invite
        except discord.NotFound:
            self.invite_cache[code] = None
        except discord.HTTPException as exc:
            _log.error("Could not fetch invite", exc)

            event.set()
            self._invite_requests.pop(code)
            raise exc

        event.set()
        self._invite_requests.pop(code)

        return invite

    async def _handle_action(
        self,
        message: discord.Message,
        actions: list[AutoModerationAction],
        reason: AutoModerationExecutionKind,
    ):
        for action in actions:
            if Automod._handle_checks(message.author, action):
                data = AutoModerationActionData._from_message(
                    message=message, reason=reason, action_taken=action, bot=self.bot
                )

                await self._execute_action(data, message=message)
                break

    async def _handle_final_action(self, member: discord.Member, actions: list[AutoModerationAction]):
        for action in actions:
            if Automod._handle_checks(member, action):
                await self._execute_final_action(member, action)
                break

    @staticmethod
    def _handle_checks(member: discord.Member, action: AutoModerationAction) -> bool:
        if action.check is None:
            return True

        check = action.check.kind

        if check is None:
            return True
        elif check == AutoModerationCheckKind.no_role:
            return not member._roles
        elif check == AutoModerationCheckKind.no_avatar:
            return member.avatar is None
        elif check == AutoModerationCheckKind.join_date:
            return (discord.utils.utcnow() - member.joined_at).total_seconds() <= action.check.time
        elif check == AutoModerationCheckKind.account_age:
            return (discord.utils.utcnow() - member.created_at).total_seconds() <= action.check.time

    async def _execute_final_action(self, member: discord.Member, action: AutoModerationAction):
        def translate(string: _) -> str:
            return global_translate(string, self.bot, member.guild.preferred_locale)

        guild = member.guild

        if self.punished_members.get((member.id, member.guild.id)):
            return
        else:
            self.punished_members[(member.id, member.guild.id)] = True

        if action.punishment.kind == AutomodFinalActionEnum.kick:
            if guild.me.guild_permissions.kick_members:
                await _logging.automod_final_log(self.bot, member, action.punishment.kind)
                await guild.kick(member, reason=translate(_("Maximum number of points reached")))
        elif action.punishment.kind == AutomodFinalActionEnum.ban:
            if guild.me.guild_permissions.ban_members:
                await _logging.automod_final_log(self.bot, member, action.punishment.kind)
                await guild.ban(member, reason=translate(_("Maximum number of points reached")))
        elif action.punishment.kind == AutomodFinalActionEnum.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = discord.utils.utcnow() + datetime.timedelta(seconds=action.punishment.duration)
                await _logging.automod_final_log(self.bot, member, action.punishment.kind, until=banned_until)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(
                        guild.id,
                        member.id,
                        TimerEnum.temp_ban,
                        banned_until,
                    )
                    await guild.ban(member, reason=translate(_("Maximum number of points reached")))
                else:
                    _log.warning("Timer Plugin is not initialized")
        elif action.punishment.kind == AutoModerationPunishmentKind.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = discord.utils.utcnow() + datetime.timedelta(seconds=action.punishment.duration)
                await _logging.automod_final_log(self.bot, member, action.punishment.kind, until=muted_until)

                await member.timeout(muted_until)

    async def _execute_action(self, data: AutoModerationActionData, message: discord.Message = None) -> None:
        guild = data.guild
        member = data.member
        automod_action = data.trigger_action

        punishment_kind = automod_action.punishment.kind

        if message is not None:
            if punishment_kind in [
                AutoModerationPunishmentKind.kick,
                AutoModerationPunishmentKind.tempmute,
                AutoModerationPunishmentKind.point,
                AutoModerationPunishmentKind.delete,
            ]:
                if message.channel.permissions_for(guild.me).manage_messages:
                    await message.delete()

        if punishment_kind != AutoModerationPunishmentKind.delete:
            # Check if the member is already punished
            if self.punished_members.get((member.id, member.guild.id)):
                return
            else:
                if punishment_kind != AutoModerationPunishmentKind.point:
                    self.punished_members[(member.id, member.guild.id)] = True

        if punishment_kind == AutoModerationPunishmentKind.ban:
            if guild.me.guild_permissions.ban_members:
                await guild.ban(member, reason=data.trigger_reason)
                await _logging.automod_log(self.bot, data)
        elif punishment_kind == AutoModerationPunishmentKind.kick:
            if guild.me.guild_permissions.kick_members:
                await guild.kick(member, reason=data.trigger_reason)
                await _logging.automod_log(self.bot, data)
        elif punishment_kind == AutoModerationPunishmentKind.delete:
            await _logging.automod_log(self.bot, data)
        elif punishment_kind == AutoModerationPunishmentKind.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = discord.utils.utcnow() + datetime.timedelta(seconds=automod_action.punishment.duration)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(guild.id, member.id, TimerEnum.temp_ban, banned_until)
                    await _logging.automod_log(self.bot, data)
                    await guild.ban(member, reason=data.trigger_reason)
                else:
                    _log.warning("Timer Plugin is not initialized")
        elif punishment_kind == AutoModerationPunishmentKind.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = discord.utils.utcnow() + datetime.timedelta(seconds=automod_action.punishment.duration)

                await member.timeout(muted_until)
                await _logging.automod_log(self.bot, data, until=muted_until)
        elif punishment_kind == AutoModerationPunishmentKind.point:
            await self._handle_points(data)

    @staticmethod
    def _is_affected(message: discord.Message, cache: ModerationModel, kind: AutoModerationExecutionKind) -> bool:
        """This function checks if the automod should be executed on the message.
        It checks for:
         - Check enabled
         - If relevant information is set
         - Exempt roles
         - Moderator roles
         - Exempt roles and channels
        """
        roles = message.author._roles
        channel = message.channel

        if not getattr(cache, f"{kind}_active") or not getattr(cache, f"{kind}_actions"):
            return False

        if any(role in cache.moderation_roles + cache.ignored_roles for role in roles):
            return False

        if any(role in getattr(cache, f"{kind}_exempt_roles") for role in roles):
            return False

        exempt_channels = getattr(cache, f"{kind}_exempt_channels")
        if channel.id in exempt_channels or channel.category_id in exempt_channels:
            return False

        return True

    async def _handle_points(self, data: AutoModerationActionData) -> None:
        guild = data.guild
        member = data.member

        points = await self.__add_points(
            member=data.member,
            points=data.trigger_action.punishment.points,
            reason=data.trigger_reason,
        )

        if points is None:
            _log.warning(f"{member.id} has no points in {guild.id}...")
            return

        new_points = data.trigger_action.punishment.points.amount
        if points - new_points < 10:
            await _logging.automod_log(self.bot, data, points=f"{points}/10 [+{new_points}]")

        if points >= 10:
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                _log.warning(f"Adding points to {member.id}, but no cache for guild {guild.id}")
                return

            await self._handle_final_action(member, cache.point_actions)
            await self.bot.db.execute(
                "UPDATE automoderation_user SET expires_at = now() WHERE user_id = $1 AND guild_id = $2 AND (expires_at IS NULL OR expires_at > now())",
                member.id,
                guild.id,
            )

    async def add_warn_points(self, member: discord.Member, moderator: discord.Member, add_points: int, reason: str):
        guild = member.guild

        points = await self.__add_points(
            member=member, points=ModerationPoints(amount=add_points, expires_in=None), reason=reason
        )
        if points is None:
            _log.warning(f"{member.id} has no points in {guild.id}...")
            return

        await _logging.warn_log(self.bot, member, moderator, reason, f"{points}/10 [+{add_points}]")

        if points >= 10:
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None or not cache.active:
                _log.warning(f"{guild.id} has no moderation cache")
                return

            await self._handle_final_action(member, cache.point_actions)

    async def __add_points(self, *, member: discord.Member, points: ModerationPoints, reason: str) -> int:
        """Add points to a member and returns the currently active points."""

        guild = member.guild
        expires_at = None

        if points.expires_in:
            expires_at = discord.utils.utcnow().replace(tzinfo=None) + datetime.timedelta(seconds=points.expires_in)

        await self.bot.db.execute(
            "INSERT INTO automoderation_user (guild_id, user_id, expires_at, points, reason) VALUES ($1, $2, $3, $4, $5)",
            guild.id,
            member.id,
            expires_at,
            points.amount,
            reason,
        )

        return await self.bot.db.fetchval(
            "SELECT SUM(points) FROM automoderation_user WHERE user_id = $1 AND guild_id = $2 AND (expires_at IS NULL OR (now() AT TIME ZONE 'utc') < expires_at)",
            member.id,
            guild.id,
        )
