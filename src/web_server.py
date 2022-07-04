from typing import TYPE_CHECKING

import tornado.log
import tornado.web

if TYPE_CHECKING:
    from main import Plyoox


class BaseHandler(tornado.web.RequestHandler):
    bot: Plyoox

    def initialize(self, bot):
        self.bot = bot

    async def prepare(self):
        await self.bot.wait_until_ready()


class CacheUpdater(BaseHandler):
    async def get(self):
        if not self.request.remote_ip == "127.0.0.1":
            return self.set_status(403)

        update = self.get_arguments("update")
        guild_id = self.get_argument("guild")

        if not update and not guild_id:
            return self.set_status(400)

        try:
            guild_id = int(guild_id)
        except ValueError:
            return self.set_status(400)

        cache = None

        if update[0] == "leveling":
            cache = self.bot.cache._leveling[guild_id]
        elif update[0] == "moderation":
            cache = self.bot.cache._moderation[guild_id]
        elif update[0] == "welcome":
            cache = self.bot.cache._welcome[guild_id]
        elif update[0] == "logging":
            cache = self.bot.cache._logging[guild_id]

        if cache is not None:
            if cache.has_key(guild_id):
                del cache[guild_id]

        return self.set_status(200)


def app(bot, database):
    extras = {"bot": bot, "db": database}

    return tornado.web.Application(
        [
            ("/update/cache", CacheUpdater, extras),
        ]
    )
