from __future__ import annotations

import asyncio
import datetime
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from lib import utils
from lib.enums import AutomodActionEnum, AutomodChecksEnum, TimerEnum, AutomodFinalActionEnum
from translation import _
from . import _logging_helper as _logging

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import AutomodExecutionModel, ModerationModel
    from lib.types import AutomodExecutionReason

_log = logging.getLogger(__name__)

DISCORD_INVITE = re.compile(r"\bdiscord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b", re.IGNORECASE)
EVERYONE_MENTION = re.compile("@(here|everyone)")
LINK_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", re.IGNORECASE)


class AutomodActionData(object):
    member: discord.Member
    trigger_content: str
    trigger_reason: str
    trigger_action: AutomodExecutionModel

    __slots__ = ("trigger_content", "member", "trigger_reason", "trigger_action")

    def __init__(self, member: discord.Member, content: str, reason: str, action: AutomodExecutionModel):
        self.member = member
        self.trigger_action = action
        self.trigger_content = content
        self.trigger_reason = reason

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f"<{name} member={self.member} trigger_action={self.trigger_action!r} trigger_content={self.trigger_content!r} trigger_reason={self.trigger_reason!r}>"

    @classmethod
    def _from_message(
        cls, *, message: discord.Message, action_taken: AutomodExecutionModel, reason: AutomodExecutionReason
    ):
        return cls(
            member=message.author,
            action=action_taken,
            content=message.content,
            reason=_(message.guild.preferred_locale, f"automod.reason.{reason}"),
        )

    @property
    def guild(self):
        return self.member.guild


class Automod(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self.invite_cache: dict[str, discord.Invite | None] = utils.ExpiringCache(seconds=600)
        self.punished_members: dict[tuple[int, int], bool] = utils.ExpiringCache(seconds=5)
        self._invite_requests: dict[str, asyncio.Event] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._run_automod(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.content and after.content != before.content:
            await self._run_automod(after)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule) -> None:
        await self.bot.db.execute("DELETE FROM automod_rules WHERE rule_id = $1", rule.id)

        self.bot.cache.remove_cache(rule.id, "automod")

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        guild = execution.guild

        if execution.action.type != discord.AutoModRuleActionType.block_message:
            return

        if (
            execution.rule_trigger_type != discord.AutoModRuleTriggerType.keyword
            and execution.rule_trigger_type != discord.AutoModRuleTriggerType.mention_spam
        ):
            return

        cache = await self.bot.cache.get_moderation_rule(execution.rule_id)
        if cache is None:
            return

        if not cache.actions:
            return

        if not guild.chunked:
            await guild.chunk()

        member = execution.member
        if member is None:
            _log.warning(f"Member {execution.user_id} not found in guild {guild.id}")
            return

        for action in cache.actions:
            if Automod._handle_checks(member, action):
                await self._execute_discord_automod(
                    data=AutomodActionData(
                        action=action,
                        member=member,
                        reason=cache.reason or _(guild.preferred_locale, "automod.reason.discord_rule"),
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

        if found_invites := DISCORD_INVITE.findall(message.content):
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                return

            if not self._is_affected(message, cache, "invite"):
                return

            invites: set[str] = set([invite[1] for invite in found_invites])
            for invite in invites:
                try:
                    fetched_invite = await self._fetch_invite(invite)

                    if fetched_invite and (
                        fetched_invite.guild.id == guild.id or fetched_invite.guild.id in cache.invite_allowed
                    ):
                        continue

                    await self._handle_action(message, cache.invite_actions, "invite")
                    return
                except discord.HTTPException:
                    break

        if found_links := LINK_REGEX.findall(message.content):
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                return

            if not self._is_affected(message, cache, "link"):
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

                await self._handle_action(message, cache.link_actions, "link")
                return

        if len(message.content) > 15 and not message.content.islower():
            len_caps = len(re.findall(r"[A-ZÄÖÜ]", message.content))
            percent = len_caps / len(message.content)

            # Only check for messages with more than 70% capital letters
            if percent < 0.7:
                return

            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                return

            if not self._is_affected(message, cache, "caps"):
                return

            await self._handle_action(message, cache.caps_actions, "caps")
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
        actions: list[AutomodExecutionModel],
        reason: AutomodExecutionReason,
    ):
        for action in actions:
            if Automod._handle_checks(message.author, action):
                data = AutomodActionData._from_message(message=message, reason=reason, action_taken=action)
                await self._execute_discord_automod(data, message=message)
                break

    async def _handle_final_action(self, member: discord.Member, actions: list[AutomodExecutionModel]):
        for action in actions:
            if Automod._handle_checks(member, action):
                await self._execute_final_action(member, action)
                break

    @staticmethod
    def _handle_checks(member: discord.Member, action: AutomodExecutionModel) -> bool:
        check = action.check

        if check is None:
            return True
        elif check == AutomodChecksEnum.no_role:
            return not member._roles
        elif check == AutomodChecksEnum.no_avatar:
            return member.avatar is None
        elif check == AutomodChecksEnum.join_date:
            return (discord.utils.utcnow() - member.joined_at).days <= action.days
        elif check == AutomodChecksEnum.account_age:
            return (discord.utils.utcnow() - member.created_at).days <= action.days

    async def _execute_final_action(self, member: discord.Member, action: AutomodExecutionModel):
        guild = member.guild
        lc = guild.preferred_locale

        if self.punished_members.get((member.id, member.guild.id)):
            return
        else:
            self.punished_members[(member.id, member.guild.id)] = True

        if action.action == AutomodFinalActionEnum.kick:
            if guild.me.guild_permissions.kick_members:
                await _logging.automod_final_log(self.bot, member, action.action)  # type: ignore
                await guild.kick(member, reason=_(lc, "automod.final.reason"))
        elif action.action == AutomodFinalActionEnum.ban:
            await _logging.automod_final_log(self.bot, member, action.action)  # type: ignore
            if guild.me.guild_permissions.ban_members:
                await guild.ban(member, reason=_(lc, "automod.final.reason"))
        elif action.action == AutomodFinalActionEnum.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = discord.utils.utcnow() + datetime.timedelta(seconds=action.duration)
                await _logging.automod_final_log(self.bot, member, action.action, until=banned_until)  # type: ignore

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(
                        guild.id,
                        member.id,
                        TimerEnum.tempban,
                        banned_until,
                    )
                    await guild.ban(member, reason=_(lc, "automod.final.reason"))
                else:
                    _log.warning("Timer Plugin is not initialized")
        elif action.action == AutomodActionEnum.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = discord.utils.utcnow() + datetime.timedelta(seconds=action.duration)
                await _logging.automod_final_log(self.bot, member, action.action, until=muted_until)  # type: ignore

                await member.timeout(muted_until)

    async def _execute_discord_automod(self, data: AutomodActionData, message: discord.Message = None) -> None:
        guild = data.guild
        member = data.member
        automod_action = data.trigger_action

        if message is not None:
            if automod_action.action in [
                AutomodActionEnum.kick,
                AutomodActionEnum.tempmute,
                AutomodActionEnum.points,
                AutomodActionEnum.delete,
            ]:
                if message.channel.permissions_for(guild.me).manage_messages:
                    await message.delete()

        if automod_action.action != AutomodActionEnum.delete:
            if self.punished_members.get((member.id, member.guild.id)):
                return
            else:
                if automod_action.action != AutomodActionEnum.points:
                    self.punished_members[(member.id, member.guild.id)] = True

        if automod_action.action == AutomodActionEnum.ban:
            if guild.me.guild_permissions.ban_members:
                await guild.ban(member, reason=data.trigger_reason)
                await _logging.automod_log(self.bot, data)
        elif automod_action.action == AutomodActionEnum.kick:
            if guild.me.guild_permissions.kick_members:
                await guild.kick(member, reason=data.trigger_reason)
                await _logging.automod_log(self.bot, data)
        elif automod_action.action == AutomodActionEnum.delete:
            await _logging.automod_log(self.bot, data)
        elif automod_action.action == AutomodActionEnum.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = discord.utils.utcnow() + datetime.timedelta(seconds=automod_action.duration)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(guild.id, member.id, TimerEnum.tempban, banned_until)
                    await _logging.automod_log(self.bot, data)
                    await guild.ban(member, reason=data.trigger_reason)
                else:
                    _log.warning("Timer Plugin is not initialized")
        elif automod_action.action == AutomodActionEnum.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = discord.utils.utcnow() + datetime.timedelta(seconds=automod_action.duration)

                await member.timeout(muted_until)
                await _logging.automod_log(self.bot, data, until=muted_until)
        elif automod_action.action == AutomodActionEnum.points:
            await self._handle_points(data)

    @staticmethod
    def _is_affected(message: discord.Message, cache: ModerationModel, kind: AutomodExecutionReason) -> bool:
        """This function checks if the automod should be executed on the message.
        It checks for:
         - Automod and check enabled
         - Relevant information is set
         - Ignored roles
         - Moderator roles
         - Whitelisted roles and channels
        """
        roles = message.author._roles
        channel = message.channel

        if not cache.active:
            return False

        if not getattr(cache, f"{kind}_active") or not getattr(cache, f"{kind}_actions"):
            return False

        if any(role in cache.mod_roles + cache.ignored_roles for role in roles):
            return False

        if channel.id in getattr(cache, f"{kind}_whitelist_channels"):
            return False

        if any(role in getattr(cache, f"{kind}_whitelist_roles") for role in roles):
            return False

        return True

    async def _handle_points(self, data: AutomodActionData) -> None:
        guild = data.guild
        member = data.member

        points = await self.__add_points(
            member=data.member,
            points=data.trigger_action.points,
            reason=data.trigger_reason,
            expires=data.trigger_action.duration,
        )

        if points is None:
            _log.warning(f"{member.id} has no points in {guild.id}...")
            return

        if points - data.trigger_action.points < 10:
            await _logging.automod_log(self.bot, data, points=f"{points}/10 [+{data.trigger_action.points}]")

        if points >= 10:
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                _log.warning(f"Adding points to {member.id}, but no cache for guild {guild.id}")
                return

            await self._handle_final_action(member, cache.automod_actions)
            await self.bot.db.execute(
                "UPDATE automod_users SET expires = now() WHERE user_id = $1 AND guild_id = $2 AND expires > now()",
                member.id,
                guild.id,
            )

    async def add_warn_points(self, member: discord.Member, moderator: discord.Member, add_points: int, reason: str):
        guild = member.guild

        points = await self.__add_points(member=member, points=add_points, reason=reason)
        if points is None:
            _log.warning(f"{member.id} has no points in {guild.id}...")
            return

        await _logging.warn_log(self.bot, member, moderator, reason, f"{points}/10 [+{add_points}]")

        if points >= 10:
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                return

            await self._handle_final_action(member, cache.automod_actions)
            await self.bot.db.execute(
                "DELETE FROM automod_users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id
            )

    async def __add_points(self, *, member: discord.Member, points: int, reason: str, expires: int = None) -> int:
        guild = member.guild
        expires_at = discord.utils.utcnow() + datetime.timedelta(seconds=expires or 1209600)

        await self.bot.db.execute(
            "INSERT INTO automod_users (guild_id, user_id, expires, points, reason) VALUES ($1, $2, $3, $4, $5)",
            guild.id,
            member.id,
            expires_at,
            points,
            reason,
        )

        return await self.bot.db.fetchval(
            "SELECT SUM(points) FROM automod_users WHERE user_id = $1 AND guild_id = $2 AND now() < expires",
            member.id,
            guild.id,
        )
