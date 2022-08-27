from __future__ import annotations

import json
from typing import TYPE_CHECKING

import discord
import tornado.web

if TYPE_CHECKING:
    from main import Plyoox
    from extensions.AutomodCache import AutomodCache


class BaseHandler(tornado.web.RequestHandler):
    bot: Plyoox

    def initialize(self, bot):
        self.bot = bot


class CacheUpdater(BaseHandler):
    async def get(self):
        update = self.get_arguments("type")
        guild_id = self.get_argument("guild")

        if not update or not guild_id:
            return self.set_status(400)

        try:
            guild_id = int(guild_id)
        except ValueError:
            return self.set_status(400)

        cache = None

        if update[0] == "leveling":
            cache = self.bot.cache._leveling
        elif update[0] == "moderation":
            cache = self.bot.cache._moderation
        elif update[0] == "welcome":
            cache = self.bot.cache._welcome
        elif update[0] == "logging":
            cache = self.bot.cache._logging

        if cache is not None:
            if cache.has_key(guild_id):
                del cache[guild_id]

        return self.set_status(200)


class TwitchNotifier(BaseHandler):
    async def get(self):
        user_id = int(self.get_argument("user_id"))
        user_name = self.get_argument("user_name")

        self.set_status(200)

        notifications = self.bot.notification
        if notifications is not None:
            await notifications.send_twitch_notification(user_id, user_name)


class AutomodState(BaseHandler):
    async def get(self):
        guild_id = self.get_argument("guild")

        if guild_id is None:
            return self.set_status(400)

        try:
            guild_id = int(guild_id)
        except ValueError:
            return self.set_status(400)

        cache: AutomodCache = self.bot.get_cog("AutomodCache")  # type: ignore

        try:
            return json.dumps(await cache.get_automod_rules(guild_id))
        except discord.Forbidden:
            return self.set_status(403)


async def start_webserver(bot: Plyoox):
    web = tornado.web.Application(
        [
            (r"/update/cache", CacheUpdater, {"bot": bot}),
            (r"/notification/twitch", TwitchNotifier, {"bot": bot}),
            (r"/fetch/automod", AutomodState, {"bot": bot}),
        ]
    )

    web.listen(8888, "127.0.0.1")
