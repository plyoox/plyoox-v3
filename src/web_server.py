from __future__ import annotations

from typing import TYPE_CHECKING

import tornado.web

if TYPE_CHECKING:
    from main import Plyoox


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
        user_id = self.get_argument("user_id")
        user_name = self.get_argument("user_name")
        viewer_count = self.get_argument("viewer_count")
        game_name = self.get_argument("game_name")
        started_at = self.get_argument("started_at")
        thumbnail_url = self.get_argument("thumbnail_url")
        title = self.get_argument("title")

        stream_data = {
            "viewer_count": viewer_count,
            "game_name": game_name,
            "started_at": started_at,
            "thumbnail_url": thumbnail_url,
            "title": title,
            "user_name": user_name,
        }

        self.set_status(200)

        await self.bot.notification.send_twitch_notification(user_id, stream_data)


async def start_webserver(bot: Plyoox):
    web = tornado.web.Application(
        [
            (r"/update/cache", CacheUpdater, {"bot": bot}),
            (r"/notification/twitch", TwitchNotifier, {"bot": bot}),
        ]
    )

    web.listen(3002)
