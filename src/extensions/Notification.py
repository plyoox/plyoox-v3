from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import emojis, extensions, helper
from translation import translate as global_translate

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import TwitchLiveNotification, Translate, TwitchOfflineNotification

_log = logging.getLogger(__name__)


class Notification(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @staticmethod
    def _get_stream_embed(
        *, data: TwitchLiveNotification, login: str, display_name: str, image_url: str, translate: Translate
    ) -> discord.Embed:
        time = data["started_at"].replace(tzinfo=datetime.timezone.utc)

        embed = extensions.Embed(
            color=0x6441A5,
            title=data["title"],
            url=f"https://twitch.tv/{login}",
            timestamp=time,
        )

        if data["game"]:
            embed.add_field(name=translate(_("Game")), value=f"> {data['game']}", inline=True)

        embed.add_field(name=translate(_("Viewer count")), value=f"> {data['viewer_count']}", inline=True)
        embed.add_field(name=translate(_("Started at")), value=f"> {utils.format_dt(time)}", inline=True)

        embed.set_image(url=data["thumbnail_url"].replace("{width}x{height}", "1920x1080"))
        embed.set_author(
            name=display_name, icon_url=f"https://static-cdn.jtvnw.net/{image_url}", url=f"https://twitch.tv/{login}"
        )

        return embed

    @staticmethod
    def _get_offline_embed(
        *, login: str, display_name: str, image_url: str, started_at: datetime.datetime, translate: Translate
    ) -> discord.Embed:
        now = discord.utils.utcnow()

        embed = extensions.Embed(
            color=0x6441A5,
            title=translate(_("Stream went offline")),
            url=f"https://twitch.tv/{login}",
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )

        embed.add_field(name=translate(_("Started at")), value=f"> {utils.format_dt(started_at)}", inline=True)
        embed.add_field(name=translate(_("Ended at")), value=f"> {utils.format_dt(now)}", inline=True)
        embed.add_field(
            name=translate(_("Duration")),
            value=f"> {helper.format_timedelta(now.replace(tzinfo=None) - started_at)}",
            inline=True,
        )

        embed.set_author(
            name=display_name, icon_url=f"https://static-cdn.jtvnw.net/{image_url}", url=f"https://twitch.tv/{login}"
        )

        return embed

    async def _delete_guild_notification(self, stream_id: int, guild_id: int):
        await self.bot.db.execute(
            "DELETE FROM twitch.live_stream WHERE stream_id = $1 AND guild_id = $2", stream_id, guild_id
        )

    async def send_twitch_notification(self, data: TwitchLiveNotification):
        def translate(string: _) -> str:
            return global_translate(string, self.bot, guild.preferred_locale)

        notification = await self.bot.db.fetchrow(
            "SELECT gs.user_id, guild_id, channel, ts.display_name, ts.login, gs.message, ts.profile_image_url, ts.display_name "
            "FROM twitch.guild_streamer gs INNER JOIN twitch.twitch_streamer ts on ts.user_id = gs.user_id WHERE gs.user_id = $1",
            data["user_id"],
        )

        if notification is None:
            return

        guild = self.bot.get_guild(notification["guild_id"])
        if guild is None:
            return

        channel = guild.get_channel(notification["channel"])

        if channel.permissions_for(guild.me).send_messages:
            message_content = notification["message"]
            embed = self._get_stream_embed(
                data=data,
                login=notification["login"],
                translate=translate,
                image_url=notification["profile_image_url"],
                display_name=notification["display_name"],
            )

            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label=translate(_("Go to Twitch")),
                    style=discord.ButtonStyle.gray,
                    url=f"https://twitch.tv/{notification['login']}",
                    emoji=emojis.twitch,
                )
            )

            message = await channel.send(
                message_content,
                allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
                view=view,
                embed=embed,
            )

            await self.bot.db.execute(
                "UPDATE twitch.live_stream SET message_id = $1 WHERE stream_id = $2 AND guild_id = $3",
                message.id,
                data["stream_id"],
                guild.id,
            )

    async def twitch_offline_edit(self, data: TwitchOfflineNotification):
        def translate(string: _) -> str:
            return global_translate(string, self.bot, guild.preferred_locale)

        notification = await self.bot.db.fetchrow(
            "SELECT ls.guild_id, gs.channel, ts.display_name, ts.login, ts.profile_image_url, ls.message_id, ls.started_at "
            "FROM twitch.live_stream ls "
            "INNER JOIN twitch.twitch_streamer ts on ts.user_id = ls.user_id "
            "INNER JOIN twitch.guild_streamer gs on ts.user_id = gs.user_id "
            "WHERE ls.stream_id = $1",
            data["stream_id"],
        )

        if notification is None:
            # This *should* never happen
            await self.bot.db.execute(
                "DELETE FROM twitch.live_stream WHERE stream_id = $1 AND guild_id", data["guild_id"]
            )
            return

        if notification is None:
            await self._delete_guild_notification(data["stream_id"], data["guild_id"])
            return

        guild = self.bot.get_guild(notification["guild_id"])
        if guild is None:
            await self._delete_guild_notification(data["stream_id"], data["guild_id"])
            return

        channel = guild.get_channel(notification["channel"])
        if channel is None:
            await self._delete_guild_notification(data["stream_id"], data["guild_id"])
            return

        if channel.permissions_for(guild.me).send_messages and notification["message_id"] is not None:
            embed = self._get_offline_embed(
                login=notification["login"],
                image_url=notification["profile_image_url"],
                started_at=notification["started_at"],
                display_name=notification["display_name"],
                translate=translate,
            )

            message = await channel.fetch_message(notification["message_id"])
            if message is not None:
                await message.edit(embed=embed, content=None, view=None)

        await self._delete_guild_notification(data["stream_id"], data["guild_id"])


async def setup(bot: Plyoox):
    await bot.add_cog(Notification(bot))
