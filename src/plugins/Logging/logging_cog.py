from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands

from lib import helper
from lib.colors import DISCORD_DEFAULT
from translation import _

if TYPE_CHECKING:
    from main import Plyoox
    from cache import LoggingModel

logger = logging.getLogger(__name__)


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def _get_cache(self, id: int) -> LoggingModel | None:
        cache = await self.bot.cache.get_logging(id)

        if cache and cache.active and cache.webhook_id is not None and cache.webhook_token is not None:
            return cache

    async def _send_message(
        self,
        guild_id: int,
        cache: LoggingModel,
        *,
        embed: discord.Embed = utils.MISSING,
        embeds: list[discord.Embed] = utils.MISSING,
    ):
        webhook = discord.Webhook.partial(cache.webhook_id, cache.webhook_token, session=self.bot.session)

        try:
            await webhook.send(embed=embed, embeds=embeds)
        except discord.NotFound:
            query_result = await self.bot.db.fetchrow(
                "UPDATE logging SET webhook_id = NULL, webhook_token = NULL WHERE id = $1 RETURNING *", guild_id
            )
            await self.bot.cache._set_logging(guild_id, query_result=query_result)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        lc = guild.preferred_locale

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_join:
            return

        embed = discord.Embed(color=DISCORD_DEFAULT)
        embed.set_author(name=_(lc, "logging.member_join.title"), icon_url=member.display_avatar)
        embed.description = _(lc, "logging.member_join.description", member=member)
        embed.add_field(
            name=_(lc, "logging.member_join.account_created"),
            value=f"> {utils.format_dt(member.joined_at)}\n{utils.format_dt(member.joined_at, 'R')}",
        )
        embed.set_footer(text=f"{_(lc, 'logging.member_id')}: {member.id}")

        await self._send_message(guild.id, cache, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        lc = guild.preferred_locale

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.member_join:
            return

        embed = discord.Embed(color=DISCORD_DEFAULT)
        embed.set_author(name=_(lc, "logging.member_leave.title"), icon_url=member.display_avatar)
        embed.set_footer(text=f"{_(lc, 'logging.member_id')}: {member.id}")
        embed.add_field(
            name=_(lc, "roles"), value=f"> {helper.format_roles(member.roles)}" or _(lc, "no_roles"), inline=False
        )
        embed.add_field(
            name=_(lc, "joined_at"),
            value=f"> {utils.format_dt(member.joined_at)}\n{utils.format_dt(member.joined_at, 'R')}",
            inline=False,
        )

        await self._send_message(member.guild.id, cache, embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        pass

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            logger.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.message_edit:
            return

        lc = guild.preferred_locale
        message = payload.cached_message

        log_embed = discord.Embed(color=DISCORD_DEFAULT)
        embeds = [log_embed]

        if message is not None:
            member = message.author

            avatar = member.display_avatar
            edit_member = member
            edit_member_id = member.id
            edit_channel = message.channel.mention

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(
                    name=_(lc, "logging.message_edit.old_message"),
                    value=message.content or _(lc, "logging.no_c ontent"),
                    inline=False,
                )
            else:
                old_message_embed = discord.Embed(color=DISCORD_DEFAULT, description=message.content)
                embeds.append(old_message_embed)
        else:
            edit_member_id = payload.data["author"]["id"]
            user_name = payload.data["author"]["id"]
            user_discriminator = payload.data["author"]["discriminator"]
            user_avatar = payload.data["author"].get("avatar", user_discriminator % len(discord.DefaultAvatar))

            avatar = f"{discord.Asset.BASE}/avatars/{edit_member_id}/{user_avatar}.webp?size=1024"
            edit_member = f"{user_name}#{user_discriminator}"
            edit_channel = f"<#{payload.channel_id}>"

        log_embed.set_author(name=_(lc, "logging.message_edit.title"), icon_url=avatar)
        log_embed.description = _(lc, "logging.message_edit.description", member=edit_member, channel=edit_channel)
        log_embed.set_footer(text=f"{_(lc, 'logging.member_id')}: {edit_member_id}")

        content = payload.data["content"]

        # messages longer than 1024 characters receive their own embed
        if len(content) <= 1024:
            log_embed.add_field(
                name=_(lc, "logging.message_edit.new_message"),
                value=content or _(lc, "logging.no_content"),
                inline=False,
            )
        else:
            new_message_embed = discord.Embed(color=DISCORD_DEFAULT, description=content)
            embeds.append(new_message_embed)

        await self._send_message(guild.id, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:  # should never happen
            logger.warning(f"Could not find guild with id {payload.guild_id}")
            return

        cache = await self._get_cache(guild.id)
        if cache is None or not cache.message_delete:
            return

        # do not log messages deleted from the logging channel
        # this prevents a logging loop
        if cache.webhook_channel == payload.channel_id:
            return

        lc = guild.preferred_locale
        message = payload.cached_message
        member = message.author if message else None

        log_embed = discord.Embed(color=DISCORD_DEFAULT)
        embeds = [log_embed]

        log_embed.set_author(
            name=_(lc, "logging.message_delete.title"), icon_url=member.display_avatar if member else None
        )

        if message is not None:
            # do not log empty messages
            if not message.content and not message.attachments:
                return

            log_embed.description = _(
                lc, "logging.message_delete.description_cached", member=member, channel=message.channel
            )
            log_embed.set_footer(text=f"{_(lc, 'logging.member_id')}: {message.author.id}")

            # messages longer than 1024 characters receive their own embed
            if len(message.content) <= 1024:
                log_embed.add_field(
                    name=_(lc, "logging.message_delete.message_content"),
                    value=message.content or _(lc, "logging.no_content"),
                    inline=False,
                )
            else:
                content_embed = discord.Embed(color=DISCORD_DEFAULT, description=message.content)
                embeds.append(content_embed)

            log_embed.add_field(
                name=_(lc, "logging.message_delete.attachment_count"),
                value=", ".join([f"`{attachment.filename}`" for attachment in message.attachments])
                if message.attachments
                else _(lc, "logging.no_attachments"),
            )
        else:
            log_embed.description = _(lc, "logging.message_delete.description_raw", channel=f"<#{payload.channel_id}>")

        await self._send_message(guild.id, cache, embeds=embeds)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        pass
