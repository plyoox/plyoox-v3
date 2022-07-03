from __future__ import annotations

import datetime
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands

from lib.enums import AutomodAction, AutomodChecks, MentionSettings, TimerType
from lib.types import AutomodExecutionReason
from translation import _
from . import _logging_helper as _logging

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import AutomodExecutionModel, ModerationModel

_log = logging.getLogger("Automod")

DISCORD_INVITE = re.compile(r"\bdiscord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b", re.IGNORECASE)
EVERYONE_MENTION = re.compile("@(here|everyone)")
LINK_REGEX = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", re.IGNORECASE)


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

                    await self.handle_action(message, cache.invite_actions, "invite")
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

                await self.handle_action(message, cache.link_actions, "link")
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

            await self.handle_action(message, cache.mention_actions, "mention")
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

            await self.handle_action(message, cache.caps_actions, "caps")
            return

    async def handle_action(
        self,
        message: discord.Message,
        actions: list[AutomodExecutionModel],
        reason: AutomodExecutionReason,
    ):
        for action in actions:
            if Automod._handle_checks(message.author, action):
                await self._execute_automod(message, action, reason)
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

    async def _execute_automod(
        self,
        message: discord.Message,
        action: AutomodExecutionModel,
        reason: AutomodExecutionReason,
    ) -> None:
        guild = message.guild
        lc = guild.preferred_locale

        automod_action = action.action

        if automod_action == AutomodAction.ban:
            if guild.me.guild_permissions.ban_members:
                await guild.ban(message.author, reason=_(lc, f"automod.reason.{automod_action}"))
                await _logging.automod_log(self.bot, message, automod_action, reason)
        elif automod_action == AutomodAction.kick:
            if guild.me.guild_permissions.kick_members:
                await guild.kick(message.author, reason=_(lc, f"automod.reason.{automod_action}"))
                await _logging.automod_log(self.bot, message, automod_action, reason)
        elif automod_action == AutomodAction.delete:
            if guild.me.guild_permissions.manage_messages:
                await message.delete()
                await _logging.automod_log(self.bot, message, automod_action, reason)
        elif automod_action == AutomodAction.points:
            pass
        elif automod_action == AutomodAction.tempban:
            if guild.me.guild_permissions.ban_members:
                banned_until = utils.utcnow() + datetime.timedelta(seconds=action.duration)

                timers = self.bot.timer
                if timers is not None:
                    await timers.create_timer(
                        guild.id,
                        message.author.id,
                        TimerType.tempban,
                        banned_until,
                    )
                    await guild.ban(message.author, reason=_(lc, f"automod.reason.{automod_action}"))
                else:
                    _log.error("Timer Plugin is not initialized")

        elif automod_action == AutomodAction.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = utils.utcnow() + datetime.timedelta(seconds=action.duration)

                await message.author.timeout(muted_until)
                await _logging.automod_log(self.bot, message, automod_action, reason, until=muted_until)

    @staticmethod
    def _is_affected(message: discord.Message, cache: ModerationModel, reason: AutomodExecutionReason) -> bool:
        """This function checks if the automod should be executed on the message.
        It checks for:
         - Automod and check are enabled
         - Relevant information is set
         - Ignored roles
         - Moderator roles
         - Whitelisted roles and channels
        """
        roles = message.author._roles
        channel = message.channel

        if (
            not cache.automod_active
            or not getattr(cache, f"{reason}_active")
            or not getattr(cache, f"{reason}_actions")
        ):
            return False

        if any(role.id in cache.mod_roles + cache.ignored_roles for role in roles):
            return False

        if channel.id in getattr(cache, f"{reason}_whitelist_channels"):
            return False

        if any(role.id in getattr(cache, f"{reason}_whitelist_roles") for role in roles):
            return False

        return True
