from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands

from lib.enums import AutomodAction, AutomodChecks
from lib.types import AutomodExecutionReason
from translation import _
from . import _logging_helper as _logging

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import AutomodExecutionModel

DISCORD_INVITE = re.compile(r"\bdiscord(?:(app)?\.com/invite?|\.gg)/([a-zA-Z0-9-]{2,32})\b")
EVERYONE_MENTION = re.compile("@(here|everyone)")


class Automod(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        channel = message.channel
        guild = message.guild
        roles = message.author._roles

        if message.author.bot:
            return

        if message.author.guild_permissions.administrator:
            return

        if found_invites := DISCORD_INVITE.findall(message.content):
            cache = await self.bot.cache.get_moderation(guild.id)

            if cache is None or not cache.invite_active or not cache.invite_actions:
                return

            if channel.id in cache.invite_whitelist_channels:
                return

            if any(role.id in cache.invite_whitelist_roles for role in roles):
                return

            invites = set([invite[1] for invite in found_invites])
            for invite in invites:
                try:
                    invite = await self.bot.fetch_invite(invite)
                    if invite.guild.id == guild.id or invite.guild.id in cache.invite_allowed:
                        continue

                    await self.handle_action(message, cache.invite_actions, "invite")
                except discord.NotFound:
                    continue
                except discord.HTTPException:
                    break

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
        print(f"Executing automod action {action.action}")
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
                pass
                # await guild.ban(message.author, reason=_(lc, f"automod.reason.{automod_action}"))
        elif automod_action == AutomodAction.tempmute:
            if guild.me.guild_permissions.mute_members:
                muted_until = utils.utcnow() + datetime.timedelta(seconds=action.duration)

                await message.author.timeout(muted_until)
                await _logging.automod_log(self.bot, message, automod_action, reason, until=muted_until)
