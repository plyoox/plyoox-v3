from __future__ import annotations

import datetime
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands

from lib.enums import AutomodAction, AutomodChecks, MentionSettings, TimerType, AutomodFinalAction
from translation import _
from . import _logging_helper as _logging

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import AutomodExecutionModel, ModerationModel
    from lib.types import AutomodExecutionReason

_log = logging.getLogger(__name__)

DISCORD_INVITE = re.compile(r"\b(https?://)?discord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b", re.IGNORECASE)
EVERYONE_MENTION = re.compile("@(here|everyone)")
LINK_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", re.IGNORECASE)


class AutomodActionData(object):
    member: discord.Member
    trigger_content: str
    trigger_reason: AutomodExecutionReason
    trigger_action: AutomodExecutionModel

    __slots__ = ("trigger_content", "member", "trigger_reason", "trigger_action")

    def __init__(
        self, member: discord.Member, content: str, reason: AutomodExecutionReason, action: AutomodExecutionModel
    ):
        self.member = member
        self.trigger_action = action
        self.trigger_content = content
        self.trigger_reason = reason

    @classmethod
    def _from_message(
        cls, *, message: discord.Message, action_taken: AutomodExecutionModel, reason: AutomodExecutionReason
    ):
        return cls(member=message.author, action=action_taken, content=message.content, reason=reason)

    @property
    def guild(self):
        return self.member.guild


class Automod(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        guild = message.guild
        author = message.author

        if author.bot:
            return

        if author.guild_permissions.administrator:
            return

        if found_invites := DISCORD_INVITE.findall(message.content):
            cache = await self.bot.cache.get_moderation(guild.id)

            if not self._is_affected(message, cache, "invite"):
                return

            invites = set([invite[1] for invite in found_invites])
            for invite in invites:
                try:
                    invite = await self.bot.fetch_invite(invite)
                    if invite.guild.id == guild.id or invite.guild.id in cache.invite_allowed:
                        continue

                    await self._handle_action(message, cache.invite_actions, "invite")
                    return
                except discord.NotFound:
                    continue
                except discord.HTTPException:
                    break

        if found_links := LINK_REGEX.findall(message.content):
            cache = await self.bot.cache.get_moderation(guild.id)

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

        mass_mentions = EVERYONE_MENTION.findall(message.content)
        if len(message.raw_mentions) + len(message.raw_role_mentions) + len(mass_mentions) > 3:
            cache = await self.bot.cache.get_moderation(guild.id)

            mentions = len([m for m in message.mentions if not m.bot or m.id != author.id])

            if cache.mention_settings == MentionSettings.include_roles:
                mentions += len(message.role_mentions)
            elif cache.mention_settings == MentionSettings.include_mass:
                mentions += len(message.role_mentions)
                mentions += len(mass_mentions)

            if mentions < cache.mention_count:
                return

            if not self._is_affected(message, cache, "mention"):
                return

            await self._handle_action(message, cache.mention_actions, "mention")
            return

        if len(message.content) > 15 and not message.content.islower():
            len_caps = len(re.findall(r"[A-ZÄÖÜ]", message.content))
            percent = len_caps / len(message.content)

            # Only check for messages with more than 70% capital letters
            if percent < 0.7:
                return

            cache = await self.bot.cache.get_moderation(guild.id)

            if not self._is_affected(message, cache, "caps"):
                return

            await self._handle_action(message, cache.caps_actions, "caps")
            return

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        guild = execution.guild

        cache = await self.bot.cache.get_moderation(guild.id)
        if cache is None or not cache.active:
            return

        automod_type: AutomodExecutionReason | None = None

        if execution.rule_trigger_type == discord.AutoModRuleTriggerType.keyword:
            automod_type = "blacklist"
        elif execution.rule_trigger_type == discord.AutoModRuleTriggerType.mention_spam:
            automod_type = "mention"

        if automod_type is None:
            return

        if not getattr(cache, automod_type + "_active"):
            return

        if not guild.chunked:
            await guild.chunk(cache=True)

        member = guild.get_member(execution.user_id)
        if member is None:
            return

        if any(role.id in (cache.mod_roles or []) + (cache.ignored_roles or []) for role in member._roles):
            return

        automod_actions = getattr(cache, automod_type + "_actions")
        if not automod_actions:
            return

        rule_actions = list(filter(lambda a: a.rule_id == execution.rule_id, automod_actions))
        if not rule_actions:
            return

        for action in rule_actions:
            if Automod._handle_checks(member, action):
                await self._execute_discord_automod(
                    data=AutomodActionData(
                        action=action, member=member, reason=automod_type, content=execution.matched_content
                    )
                )

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
        elif check == AutomodChecks.no_role:
            return not member._roles
        elif check == AutomodChecks.no_avatar:
            return member.avatar is None
        elif check == AutomodChecks.join_date:
            days = action.days

            return (utils.utcnow() - member.joined_at).days <= days
        elif check == AutomodChecks.account_age:
            days = action.days

            return (utils.utcnow() - member.created_at).days <= days

    async def _execute_final_action(self, member: discord.Member, action: AutomodExecutionModel):
        guild = member.guild
        lc = guild.preferred_locale

        await _logging.automod_final_log(self.bot, member, action.action)  # type: ignore

        if action.action == AutomodFinalAction.kick:
            if guild.me.guild_permissions.kick_members:
                await guild.kick(member, reason=_(lc, "automod.final.reason"))
        elif action.action == AutomodFinalAction.ban:
            if guild.me.guild_permissions.ban_members:
                await guild.ban(member, reason=_(lc, "automod.final.reason"))

        elif action.action == AutomodFinalAction.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = utils.utcnow() + datetime.timedelta(seconds=action.duration)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(
                        guild.id,
                        member.id,
                        TimerType.tempban,
                        banned_until,
                    )
                    await guild.ban(member, reason=_(lc, "automod.final.reason"))
                else:
                    _log.error("Timer Plugin is not initialized")

        elif action.action == AutomodAction.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = utils.utcnow() + datetime.timedelta(seconds=action.duration)
                await member.timeout(muted_until)

    async def _execute_discord_automod(self, data: AutomodActionData, message: discord.Message = None) -> None:
        guild = data.guild
        member = data.member
        lc = guild.preferred_locale
        automod_action = data.trigger_action

        if message is not None:
            if automod_action in [AutomodAction.kick, AutomodAction.tempmute, AutomodAction.points]:
                if message.channel.permissions_for(guild.me).manage_messages:
                    await message.delete()

        if automod_action == AutomodAction.ban:
            if guild.me.guild_permissions.ban_members:
                await guild.ban(member, reason=_(lc, f"automod.reason.{data.trigger_reason}"))
                await _logging.automod_log(self.bot, data)
        elif automod_action == AutomodAction.kick:
            if guild.me.guild_permissions.kick_members:
                await guild.kick(member, reason=_(lc, f"automod.reason.{data.trigger_reason}"))
                await _logging.automod_log(self.bot, data)
        elif automod_action == AutomodAction.delete:
            await _logging.automod_log(self.bot, data)
        elif automod_action == AutomodAction.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = utils.utcnow() + datetime.timedelta(seconds=data.trigger_action.duration)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(guild.id, member.id, TimerType.tempban, banned_until)
                    await _logging.automod_log(self.bot, data)
                    await guild.ban(member, reason=_(lc, f"automod.reason.{automod_action}"))
                else:
                    _log.error("Timer Plugin is not initialized")

        elif automod_action == AutomodAction.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = utils.utcnow() + datetime.timedelta(seconds=data.trigger_action.duration)

                await member.timeout(muted_until)
                await _logging.automod_log(self.bot, data, until=muted_until)
        elif automod_action == AutomodAction.points:
            await self._handle_points(data)

    @staticmethod
    def _is_affected(message: discord.Message, cache: ModerationModel, reason: AutomodExecutionReason) -> bool:
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

        if not getattr(cache, f"{reason}_active") or not getattr(cache, f"{reason}_actions"):
            return False

        if any(role.id in (cache.mod_roles or []) + (cache.ignored_roles or []) for role in roles):
            return False

        if channel.id in getattr(cache, f"{reason}_whitelist_channels"):
            return False

        if any(role.id in getattr(cache, f"{reason}_whitelist_roles") for role in roles):
            return False

        return True

    async def _handle_points(self, data: AutomodActionData) -> None:
        guild = data.guild
        member = data.member

        points = await self.__add_points(
            data.member, data.trigger_action.points, _(guild.preferred_locale, f"automod.reason.{data.trigger_reason}")
        )

        if points is None:
            _log.warning(f"{member.id} has no points in {guild.id}...")
            return

        # await message.delete()
        await _logging.automod_log(self.bot, data, points=f"{points}/10 [+{data.trigger_action.points}]")

        if points >= 10:
            cache = await self.bot.cache.get_moderation(guild.id)
            if cache is None:
                return

            await self._handle_final_action(member, cache.automod_actions)
            await self.bot.db.execute(
                "DELETE FROM automod_users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id
            )

    async def add_warn_points(self, member: discord.Member, moderator: discord.Member, add_points: int, reason: str):
        guild = member.guild

        points = await self.__add_points(member, add_points, reason)
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

    async def __add_points(self, member: discord.Member, points: int, reason: str) -> int:
        guild = member.guild

        await self.bot.db.execute(
            "INSERT INTO automod_users (guild_id, user_id, timestamp, points, reason) VALUES ($1, $2, $3, $4, $5)",
            guild.id,
            member.id,
            utils.utcnow(),
            points,
            reason,
        )

        points = await self.bot.db.fetchval(
            "SELECT SUM(points) FROM automod_users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id
        )

        return points
