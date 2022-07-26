from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


_log = logging.getLogger(__name__)


class Notification(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self.twitch_access_token = {}

    async def _get_access_token(self) -> str | None:
        valid_until = self.twitch_access_token.get("valid_until")
        if valid_until is not None and valid_until > discord.utils.utcnow():
            return self.twitch_access_token["access_token"]

        body = {
            "Client-Id": os.getenv("TWITCH_CLIENT_ID"),
            "Client-Secret": os.getenv("TWITCH_CLIENT_SECRET"),
            "Grant-Type": "client_credentials",
        }

        async with self.bot.session.post("https://id.twitch.tv/oauth2/token", data=body) as res:
            data = await res.json()

            if res.status == 200:
                self.twitch_access_token = {
                    "access_token": data["access_token"],
                    "valid_until": discord.utils.utcnow() + datetime.timedelta(seconds=data["expires_in"]),
                }
                return data["access_token"]

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.db.execute(
            "DELETE FROM twitch_notifications WHERE guild_id = $1 RETURNING user_id",
            guild.id,
        )

        event_sub_ids = await self.bot.db.fetch(
            "DELETE FROM twitch_users WHERE (SELECT count(user_id) FROM twitch_notifications) = 0 RETURNING eventsub_id",
            guild.id,
        )

        app_token = await self._get_access_token()
        if app_token is None:
            _log.error("Could not fetch Twitch access token.")

        headers = {
            "Client-Id": os.getenv("TWITCH_CLIENT_ID"),
            "Authorization": f"Bearer {app_token}",
        }

        for event_sub in event_sub_ids:
            async with self.bot.session.delete(
                f"https://api.twitch.tv/helix/eventsub/subscriptions?id={event_sub['eventsub_id']}", headers=headers
            ) as res:
                if res.status != 200:
                    _log.error(f"Deleting event subscription {event_sub} failed with status {res.status}.")

    async def send_twitch_notification(self, user_id: int, user_name: str):
        notifications = await self.bot.db.fetch(
            "SELECT id, guild_id, channel_id, message FROM twitch_notifications WHERE user_id = $1", user_id
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
                message = notification["message"].replace("{link}", f"https://twitch.tv/{user_name}")

                await channel.send(message)
                await asyncio.sleep(0.2)


async def setup(bot: Plyoox):
    await bot.add_cog(Notification(bot))
