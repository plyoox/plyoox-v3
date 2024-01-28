from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import helper, extensions
from lib.enums import LoggingKind
from translation.translator import translate as global_translate

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import LoggingSettings

_log = logging.getLogger(__name__)

ERROR_COLOR = discord.Color.red()
WARN_COLOR = discord.Color.orange()
SUCCESS_COLOR = discord.Color.green()
INFO_COLOR = discord.Color.blue()


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def _get_setting(self, id: int, kind: LoggingKind) -> LoggingSettings | None:
        """Returns the logging settings for the given guild id and kind.
        Only returns the settings if the logging is active and a channel is set.
        """

        cache = await self.bot.cache.get_logging(id)

        if not cache:
            return

        settings = cache.settings.get(kind)
        if settings and settings.channel:
            return settings

    async def _send_message(
        self,
        guild: discord.Guild,
        cache: LoggingSettings,
        *,
        file: discord.File = utils.MISSING,
        embeds: list[discord.Embed] = utils.MISSING,
    ):
        # Normally all logging channels should be webhook channels,
        # but just in case (e.g. manual insertion)
        if cache.channel.token is None:
            channel = guild.get_channel(cache.channel.id)  # channel is a text channel
            if channel is None or not channel.permissions_for(guild.me).send_messages:
                _log.info(f"Deleted logging channel {cache.channel} due to missing permissions")

                await self.bot.db.execute(
                    "DELETE FROM maybe_webhook WHERE id = $1 AND guild_id = $2",
                    cache.channel.id,
                    guild.id,
                )

                self.bot.cache.remove_cache(guild.id, "log")
            else:
                try:
                    await channel.send(file=file, embeds=embeds)
                except Exception as e:
                    _log.error(f"Could not logging message to channel {channel}", exc_info=e)
        else:
            webhook = discord.Webhook.partial(cache.channel.id, cache.channel.token, session=self.bot.session)

            try:
                await webhook.send(embeds=embeds, file=file)
            except discord.NotFound:
                _log.info(f"Deleted logging webhook {repr(cache.channel)} due to missing webhook")

                await self.bot.db.execute("DELETE FROM maybe_webhook WHERE id = $1", cache.channel.id)

                self.bot.cache.edit_cache(guild.id, "log", webhook_token=None, webhook_id=None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        guild = member.guild

        cache = await self._get_setting(guild.id, LoggingKind.member_join)
        if cache is None:
            return

        # Members that join *can* have a role, for example the twitch integration role
        # is added before the member joins the guild.
        if any(role in cache.exempt_roles for role in member.roles):
            return

        embed = extensions.Embed(
            description=translate(_("The user {member.name} joined the guild.")).format(member=member),
            color=SUCCESS_COLOR,
        )
        embed.set_author(name=translate(_("User joined")), icon_url=member.display_avatar)
        embed.add_field(
            name=translate(_("Account created at")),
            value=helper.embed_timestamp_format(member.created_at),
        )
        embed.set_footer(text=f"{translate(_('User id'))}: {member.id}")

        await self._send_message(guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        def translate(string: _):
            return global_translate(string, self.bot, member.guild.preferred_locale)

        guild = member.guild

        cache = await self._get_setting(guild.id, LoggingKind.member_leave)
        if cache is None:
            return

        if any(role in cache.exempt_roles for role in member.roles):
            return

        embed = extensions.Embed(
            description=translate(_("The user {member.name} left the guild.")).format(member=member),
            color=ERROR_COLOR,
        )
        embed.set_author(name=translate(_("Member left")), icon_url=member.display_avatar)
        embed.add_field(name=translate(_("Account created at")), value=helper.embed_timestamp_format(member.created_at))

        roles = helper.format_roles(member.roles)
        embed.add_field(name=translate(_("Roles")), value=f"> {roles}" if roles else translate(_("No roles")))

        embed.add_field(name=translate(_("Joined at")), value=helper.embed_timestamp_format(member.joined_at))
        embed.set_footer(text=f"{translate(_('User id'))}: {member.id}")

        await self._send_message(member.guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        cache = await self._get_setting(guild.id, LoggingKind.member_ban)
        if cache is None:
            return

        if any(role in cache.exempt_roles for role in user.roles):
            return

        embed = extensions.Embed(color=ERROR_COLOR)
        embed.add_field(name=translate(_("Account created at")), value=helper.embed_timestamp_format(user.created_at))
        embed.set_footer(text=f"{global_translate(_('User id'), self.bot, guild.preferred_locale)}: {user.id}")

        if isinstance(user, discord.Member):
            embed.set_author(name=translate(_("User banned")), icon_url=user.display_avatar)
            embed.add_field(name=translate(_("Joined at")), value=helper.embed_timestamp_format(user.joined_at))

            roles = helper.format_roles(user.roles)
            embed.add_field(name=translate(_("Roles")), value=f"> {roles}" if roles else translate(_("No roles")))

        else:
            embed.set_author(name=translate(_("User banned")), icon_url=user.display_avatar)

        await self._send_message(guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        cache = await self._get_setting(guild.id, LoggingKind.member_unban)
        if cache is None:
            return

        embed = extensions.Embed(color=WARN_COLOR)
        embed.set_author(name=translate(_("Member unbanned")), icon_url=user.display_avatar)
        embed.set_footer(text=f"{translate(_('User id'))}: {user.id}")
        embed.add_field(name=translate(_("Account created at")), value=helper.embed_timestamp_format(user.created_at))

        await self._send_message(guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        guild = after.guild

        if before.roles != after.roles:
            cache = await self._get_setting(guild.id, LoggingKind.member_role_update)
            if cache is None:
                return

            if any(role in cache.exempt_roles for role in after.roles):
                return

            embed = extensions.Embed(color=INFO_COLOR)
            embed.set_author(name=translate(_("Member roles changed")), icon_url=before.display_avatar)
            embed.set_footer(text=f"{translate(_('User id'))}: {before.id}")

            new_roles = helper.format_roles(after.roles)
            embed.add_field(
                name=translate(_("New roles")), value=f"> {new_roles}" if new_roles else translate(_("No roles"))
            )

            old_roles = helper.format_roles(before.roles)
            embed.add_field(
                name=translate(_("Old roles")), value=f"> {old_roles}" if old_roles else translate(_("No roles"))
            )

            await self._send_message(guild, cache, embeds=[embed])
        elif before.display_name != after.display_name:
            cache = await self._get_setting(guild.id, LoggingKind.member_rename)
            if cache is None:
                return

            if any(role in cache.exempt_roles for role in after.roles):
                return

            embed = extensions.Embed(color=INFO_COLOR)
            embed.set_author(name=translate(_("Member renamed")), icon_url=after.display_avatar)
            embed.set_footer(text=f"{translate(_('User id'))}: {before.id}")

            embed.add_field(
                name=translate(_("Previous name")),
                value=f"> {before.display_name}",
            )

            embed.add_field(
                name=translate(_("New name")),
                value=f"> {after.display_name}",
            )

            await self._send_message(guild, cache, embeds=[embed])

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        if payload.data.get("author") is None or payload.data["author"].get("bot"):
            return  # ignore bots due to interaction edits

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            _log.warning(f"Could not find guild {payload.guild_id}")
            return

        cache = await self._get_setting(guild.id, LoggingKind.message_edit)
        if cache is None:
            return

        # Ignore exempt channels
        if payload.channel_id in cache.exempt_channels:
            return

        # Also check if parent is exempt
        if channel := guild.get_channel(payload.channel_id):
            if channel.category_id in cache.exempt_channels:
                return

        # Ignore exempt roles
        if any(role in cache.exempt_roles for role in payload.data["member"].get("roles", [])):
            return

        log_embed = extensions.Embed(color=WARN_COLOR)
        embeds = [log_embed]

        if message := payload.cached_message:
            member = message.author

            avatar = member.display_avatar
            edit_member = member
            edit_member_id = member.id
            edit_channel = message.channel.mention

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(
                    name=translate(_("Old message content")), value=message.content or translate(_("No content"))
                )
            else:
                old_message_embed = extensions.Embed(description=message.content, color=WARN_COLOR)
                embeds.append(old_message_embed)
        else:
            edit_member_id = payload.data["author"]["id"]
            user_name = payload.data["author"]["username"]
            user_discriminator = payload.data["author"]["discriminator"]
            user_avatar = payload.data["author"].get("avatar", int(user_discriminator) % len(discord.DefaultAvatar))
            edit_channel = f"<#{payload.channel_id}>"

            avatar = f"{discord.Asset.BASE}/avatars/{edit_member_id}/{user_avatar}.webp?size=1024"

            if user_discriminator == "0":
                edit_member = f"{user_name}"
            else:
                edit_member = f"{user_name}#{user_discriminator}"

        jump_to_url = f"https://canary.discord.com/channels/{guild.id}/{payload.channel_id}/{payload.message_id}"

        log_embed.description = translate(_("**{member}** edited a [message]({message}) in {channel}.")).format(
            member=edit_member, channel=edit_channel, message=jump_to_url
        )
        log_embed.set_author(name=translate(_("Message edited")), icon_url=avatar)
        log_embed.set_footer(text=f"{translate(_('User id'))}: {edit_member_id}")

        content = payload.data.get("content") or translate(_("No content"))

        # messages longer than 1024 characters receive their own embed
        if len(content) <= 1024:
            log_embed.add_field(name=translate(_("New message content")), value=content)
        else:
            new_message_embed = extensions.Embed(description=content, color=WARN_COLOR)
            embeds.append(new_message_embed)

        await self._send_message(guild, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            _log.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_setting(guild.id, LoggingKind.message_delete)
        if cache is None:
            return

        if payload.channel_id in cache.exempt_channels:
            return

        # Also check if parent is exempt
        if channel := guild.get_channel(payload.channel_id):
            if channel.category_id in cache.exempt_channels:
                return

        # do not log messages deleted from the logging channel
        # this prevents a logging loop
        webhook_channel = cache.channel
        if webhook_channel.token is None:
            if webhook_channel.id == payload.channel_id:
                return
        else:
            if webhook_channel.webhook_channel == payload.channel_id:
                return

        message = payload.cached_message
        member = message.author if message else None

        log_embed = extensions.Embed(color=ERROR_COLOR)
        embeds = [log_embed]

        log_embed.set_author(name=translate(_("Message deleted")), icon_url=member.display_avatar if member else None)

        if message is not None and isinstance(member, discord.Member):
            # do not log empty messages
            if not message.content and not message.attachments:
                return

            log_embed.description = translate(_("A message from **{member}** was deleted from {channel.mention}.")).format(
                member=member, channel=message.channel
            )
            log_embed.set_footer(text=f"{translate(_('User id'))}: {member.id}")

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(
                    name=translate(_("Message content")),
                    value=message.content or translate(_("No content")),
                )
            else:
                content_embed = extensions.Embed(description=message.content, color=ERROR_COLOR)
                embeds.append(content_embed)

            if message.attachments:
                log_embed.add_field(
                    name=translate(_("Attachments")),
                    value=", ".join([f"`{attachment.filename}`" for attachment in message.attachments]),
                )
        else:
            log_embed.description = translate(_("A message from {channel} has been deleted.")).format(
                channel=f"<#{payload.channel_id}>",
            )

        await self._send_message(guild, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        def translate(string: _):
            return global_translate(string, self.bot, guild.preferred_locale)

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            _log.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_setting(guild.id, LoggingKind.message_delete)
        if cache is None:
            return

        # Check for exempt channels
        if payload.channel_id in cache.exempt_channels:
            return

        # Also check if parent is exempt
        if channel := guild.get_channel(payload.channel_id):
            if channel.category_id in cache.exempt_channels:
                return

        # do not log messages deleted from the logging channel
        # this prevents a logging loop
        webhook_channel = cache.channel

        if webhook_channel.token is None:
            if webhook_channel.id == payload.channel_id:
                return
        else:
            if webhook_channel.webhook_channel == payload.channel_id:
                return

        embed = extensions.Embed(
            title=translate(_("Bulk message delete")),
            color=ERROR_COLOR,
            description=translate(_("{count} messages have been deleted from {channel}.")).format(
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

        await self._send_message(guild, cache, embeds=[embed], file=file)


async def setup(bot: Plyoox):
    await bot.add_cog(LoggingEvents(bot))
