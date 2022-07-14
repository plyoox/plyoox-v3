from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class Notification(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def send_twitch_notification(self, user_id: int, user_name: str):
        notification = await self.bot.db.fetch(
            "SELECT id, guild_id, channel_id, message FROM twitch_notifications WHERE user_id = $1", user_id
        )

        for notification in notification:
            guild = self.bot.get_guild(notification["guild_id"])
            if guild is None:
                continue

            channel = guild.get_channel(notification["channel_id"])
            if channel is None:
                await self.bot.db.execute("DELETE FROM twitch_notifications WHERE id = $1", notification["id"])

            if channel.permissions_for(guild.me).send_messages:
                await channel.send(notification["message"].replace("{link}", f"https://twitch.tv/{user_name}"))
                await asyncio.sleep(0.2)


async def setup(bot: Plyoox):
    await bot.add_cog(Notification(bot))
