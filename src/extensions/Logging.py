from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import helper, extensions
from translation.translator import translate

if TYPE_CHECKING:
    from main import Plyoox
    from cache import LoggingModel

_log = logging.getLogger(__name__)


ERROR_COLOR = discord.Color.red()
WARN_COLOR = discord.Color.orange()
SUCCESS_COLOR = discord.Color.green()
INFO_COLOR = discord.Color.blue()


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def _get_cache(self, id: int) -> LoggingModel | None:
        cache = await self.bot.cache.get_logging(id)

        if cache and cache.active and cache.webhook_id is not None and cache.webhook_token is not None:
            return cache

    async def _send_message(
        self,
        guild: discord.Guild,
        cache: LoggingModel,
        *,
        file: discord.File = utils.MISSING,
        embeds: list[discord.Embed] = utils.MISSING,
    ):
        webhook = discord.Webhook.partial(cache.webhook_id, cache.webhook_token, session=self.bot.session)

        if embeds is not utils.MISSING:
            for embed in embeds:
                embed._update_locale(guild.preferred_locale, self.bot.tree.translator)

        try:
            await webhook.send(embeds=embeds, file=file)
        except discord.NotFound:
            await self.bot.db.execute(
                "UPDATE logging SET webhook_id = NULL, webhook_token = NULL WHERE id = $1", guild.id
            )

            self.bot.cache.edit_cache(guild.id, "log", webhook_token=None, webhook_id=None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_join:
            return

        embed = extensions.Embed(
            description=translate(
                _("The user {member.name} joined the guild."), self.bot, guild.preferred_locale
            ).format(member=member),
            color=SUCCESS_COLOR,
        )
        embed.set_author(name=_("Member joined"), icon_url=member.display_avatar)
        embed.add_field(
            name=_("Account created at"),
            value=helper.embed_timestamp_format(member.created_at),
        )
        embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {member.id}")

        await self._send_message(guild, cache, embed=[embed])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_join:
            return

        embed = extensions.Embed(
            description=translate(_("The user {member.name} left the guild."), self.bot, guild.preferred_locale).format(
                member=member
            ),
            color=ERROR_COLOR,
        )
        embed.set_author(name=_("Member left"), icon_url=member.display_avatar)
        embed.add_field(name=_("Account created at"), value=helper.embed_timestamp_format(member.created_at))

        roles = helper.format_roles(member.roles)
        if roles:
            embed.add_field(name=_("Roles"), value=f"> {roles}")
        else:
            embed.add_field(name=_("Roles"), value=_("No roles"))

        embed.add_field(name=_("Joined at"), value=helper.embed_timestamp_format(member.joined_at))
        embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {member.id}")

        await self._send_message(member.guild, cache, embed=[embed])

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_ban:
            return

        embed = extensions.Embed(color=ERROR_COLOR)
        embed.add_field(name=_("Account created at"), value=helper.embed_timestamp_format(user.created_at))
        embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {user.id}")

        if isinstance(user, discord.Member):
            embed.set_author(name=_("Member banned"), icon_url=user.display_avatar)
            embed.add_field(name=_("Joined at"), value=helper.embed_timestamp_format(user.joined_at))

            roles = helper.format_roles(user.roles)
            embed.add_field(name=_("Roles"), value=f"> {roles}" if roles else _("No roles"))

        else:
            embed.set_author(name=_("User banned"), icon_url=user.display_avatar)

        await self._send_message(guild, cache, embed={embed})

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_unban:
            return

        embed = extensions.Embed(color=WARN_COLOR)
        embed.set_author(name=_("Member unbanned"), icon_url=user.display_avatar)
        embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {user.id}")
        embed.add_field(name=_("Account created at"), value=helper.embed_timestamp_format(user.created_at))

        await self._send_message(guild, cache, embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild
        cache = await self._get_cache(before.guild.id)
        if cache is None:
            return

        if cache.member_role_change and before.roles != after.roles:
            embed = extensions.Embed(color=INFO_COLOR)
            embed.set_author(name=_("Member roles changed"), icon_url=before.display_avatar)
            embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {before.id}")

            new_roles = helper.format_roles(after.roles)
            embed.add_field(name=_("New roles"), value=f"> {new_roles}" if new_roles else _("No roles"))

            old_roles = helper.format_roles(before.roles)
            embed.add_field(name=_("Old roles"), value=f"> {old_roles}" if old_roles else _("No roles"))

            await self._send_message(guild, cache, embed=[embed])
        elif cache.member_rename and before.display_name != after.display_name:
            embed = extensions.Embed(color=INFO_COLOR)
            embed.set_author(name=_("Member renamed"), icon_url=after.display_avatar)
            embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {before.id}")

            embed.add_field(
                name=_("Previous name"),
                value=f"> {before.display_name}",
            )

            embed.add_field(
                name=_("New name"),
                value=f"> {after.display_name}",
            )

            await self._send_message(guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.data.get("author") is None or payload.data["author"].get("bot"):
            return  # ignore bots due to interaction edits

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            _log.warning(f"Could not find guild {payload.guild_id}")
            return

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.message_edit:
            return

        message = payload.cached_message

        log_embed = extensions.Embed(color=WARN_COLOR)
        embeds = [log_embed]

        if message is not None:
            member = message.author

            avatar = member.display_avatar
            edit_member = member
            edit_member_id = member.id
            edit_channel = message.channel.mention

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(name=_("Old message content"), value=message.content or _("No content"))
            else:
                old_message_embed = extensions.Embed(description=message.content, color=WARN_COLOR)
                embeds.append(old_message_embed)
        else:
            edit_member_id = payload.data["author"]["id"]
            user_name = payload.data["author"]["username"]
            user_discriminator = payload.data["author"]["discriminator"]
            user_avatar = payload.data["author"].get("avatar", int(user_discriminator) % len(discord.DefaultAvatar))

            avatar = f"{discord.Asset.BASE}/avatars/{edit_member_id}/{user_avatar}.webp?size=1024"
            edit_member = f"{user_name}#{user_discriminator}"
            edit_channel = f"<#{payload.channel_id}>"

        log_embed.description = translate(
            _("logging.message_edit.description"), self.bot, guild.preferred_locale
        ).format(member=edit_member, channel=edit_channel)
        log_embed.set_author(name=_("Message edited"), icon_url=avatar)
        log_embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {member.id}")

        content = payload.data.get("content") or _("No content")

        # messages longer than 1024 characters receive their own embed
        if len(content) <= 1024:
            log_embed.add_field(name=_("New message content"), value=content)
        else:
            new_message_embed = extensions.Embed(description=content, color=WARN_COLOR)
            embeds.append(new_message_embed)

        await self._send_message(guild, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            _log.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.message_delete:
            return

        # do not log messages deleted from the logging channel
        # this prevents a logging loop
        if cache.webhook_channel == payload.channel_id:
            return

        message = payload.cached_message
        member = message.author if message else None

        log_embed = extensions.Embed(color=ERROR_COLOR)
        embeds = [log_embed]

        log_embed.set_author(name=_("Message deleted"), icon_url=member.display_avatar if member else None)

        if message is not None and isinstance(member, discord.Member):
            # do not log empty messages
            if not message.content and not message.attachments:
                return

            log_embed.description = translate(
                _("A message from **{member}** was deleted from {channel.mention}.")
            ).format(member=member, channel=message.channel)
            log_embed.set_footer(text=f"{translate(_('User id'), self.bot, guild.preferred_locale)}: {member.id}")

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(
                    name=_("Message content"),
                    value=message.content or _("No content"),
                )
            else:
                content_embed = extensions.Embed(description=message.content, color=ERROR_COLOR)
                embeds.append(content_embed)

            if message.attachments:
                log_embed.add_field(
                    name=_("Attachments"),
                    value=", ".join([f"`{attachment.filename}`" for attachment in message.attachments]),
                )
        else:
            log_embed.description = translate(
                _("A message from {channel} has been deleted.", self.bot, guild.preferred_locale)
            ).format(
                channel=f"<#{payload.channel_id}>",
            )

        await self._send_message(guild, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            _log.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.message_delete:
            return

        # do not log messages deleted from the logging channel
        # this prevents a logging loop
        if cache.webhook_channel == payload.channel_id:
            return

        embed = extensions.Embed(
            title=_("Bulk message delete"),
            color=ERROR_COLOR,
            description=translate(_("logging.bulk_delete.description")).format(
                count=len(payload.message_ids),
                channel=f"<#{payload.channel_id}>",
            ),
        )

        file = discord.utils.MISSING

        if len(payload.cached_messages):
            messages = [
                f"{msg.author} ({msg.author.id}):\t\t{msg.content}" for msg in payload.cached_messages if msg.content
            ]

            if len(messages) > 0:
                _file = io.BytesIO()
                _file.write("\n".join([msg for msg in messages]).encode("utf-8"))
                _file.seek(0)

                file = discord.File(_file, filename="deleted_messages.txt")

        await self._send_message(guild, cache, embed=[embed], file=file)


async def setup(bot: Plyoox):
    await bot.add_cog(LoggingEvents(bot))
