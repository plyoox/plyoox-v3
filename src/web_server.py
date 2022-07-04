from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

import tornado.log
import tornado.web

if TYPE_CHECKING:
    from main import Plyoox


logger = logging.getLogger("tornado.application")
logger.setLevel(logging.ERROR)
tornado.log.enable_pretty_logging(logger=logger)


class BaseHandler(tornado.web.RequestHandler):
    bot: Plyoox

    def initialize(self, bot):
        self.bot = bot


class CacheUpdater(BaseHandler):
    async def get(self):
        if self.request.remote_ip not in ["::1", "127.0.0.1"]:
            return self.set_status(403)

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


async def start_webserver(bot: Plyoox):
    web = tornado.web.Application(
        [
            (r"/update/cache", CacheUpdater, {"bot": bot}),
        ]
    )

    web.listen(8888)
