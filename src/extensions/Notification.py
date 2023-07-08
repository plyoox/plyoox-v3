from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from lib import emojis, extensions, helper
from translation import _

if TYPE_CHECKING:
    from main import Plyoox

_log = logging.getLogger(__name__)


class Notification(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @staticmethod
    async def _get_stream_embed(data: dict[str, Any], lc: discord.Locale) -> discord.Embed:
        time = datetime.datetime.strptime(data["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc
        )

        embed = extensions.Embed(
            color=0x6441A5, title=data["title"], url=f"https://twitch.tv/{data['user_name']}", timestamp=time
        )
        if data["game_name"]:
            embed.add_field(name=_(lc, "notifications.game"), value=f"> {data['game_name']}")
        embed.add_field(name=_(lc, "notifications.viewer_count"), value=f"> {data['viewer_count']}")
        embed.add_field(name=_(lc, "notifications.started_at"), value=helper.embed_timestamp_format(time))

        embed.set_image(url=data["thumbnail_url"])

        return embed

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        if guild.id is None:
            return

        async with self.bot.session.delete(
            f"{self.bot.notificator_url}/service/twitch/notifications/guild/{guild.id}"
        ) as res:
            if res.status > 399:
                data = await res.text()
                _log.warning(
                    f"Received bad status code when deleting eventsub from guild ({guild.id}): {res.status}\n{data}"
                )

    async def send_twitch_notification(self, user_id: str, stream_data: dict):
        notifications = await self.bot.db.fetch(
            "SELECT id, guild_id, channel_id, message FROM twitch_notifications WHERE user_id = $1", int(user_id)
        )

        for notification in notifications:
            if notification["message"] is None:
                continue

            guild = self.bot.get_guild(notification["guild_id"])
            if guild is None:
                continue

            channel = guild.get_channel(notification["channel_id"])
            if channel is None:
                await self.bot.db.execute("DELETE FROM twitch_notifications WHERE id = $1", notification["id"])

            if channel.permissions_for(guild.me).send_messages:
                message = notification["message"].replace("{link}", f"https://twitch.tv/{stream_data['user_name']}")
                embed = await self._get_stream_embed(stream_data, guild.preferred_locale)

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label=_(guild.preferred_locale, "notifications.twitch_button"),
                        style=discord.ButtonStyle.gray,
                        url=f"https://twitch.tv/{stream_data['user_name']}",
                        emoji=emojis.twitch,
                    )
                )

                await channel.send(
                    message,
                    allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
                    view=view,
                    embed=embed,
                )


async def setup(bot: Plyoox):
    await bot.add_cog(Notification(bot))
