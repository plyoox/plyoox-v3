from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands

from translation import _
from utils import colors

if TYPE_CHECKING:
    from src.main import Plyoox
    from src.cache.models import LoggingModel


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def _get_cache(self, id: int) -> LoggingModel | None:
        cache = await self.bot.cache.get_logging(id)

        if cache and cache.active and cache.webhook_id and cache.webhook_token:
            return cache

    async def _send_message(self, id: int, cache: LoggingModel, embed: discord.Embed):
        webhook = discord.Webhook.partial(cache.webhook_id, cache.webhook_token, session=self.bot.session)

        try:
            await webhook.send(embed=embed)
        except discord.Forbidden:
            query_result = await self.bot.db.fetchrow(
                "UPDATE logging SET webhook_id = NULL, webhook_token = NULL WHERE id = $1 RETURNING *", id
            )
            await self.bot.cache._set_logging(id, query_result=query_result)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        lc = guild.preferred_locale
        cache = await self._get_cache(guild.id)

        if cache is None:
            return

        embed = discord.Embed(color=colors.DISCORD_DEFAULT)
        embed.set_author(name=_(lc, "logging.member_join.title"), icon_url=member.display_avatar)
        embed.description = _(lc, "logging.member_join.description", member=member)
        embed.add_field(
            name=_(lc, "logging.member_join.account_created"), value=f"> {utils.format_dt(member.created_at, 'R')}"
        )
        embed.set_footer(text=f"{_(lc, 'id')}: {member.id}")

        await self._send_message(guild.id, cache, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass

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
        pass

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        pass

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        pass
