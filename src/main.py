import asyncio
import os
from datetime import datetime

import asyncpg
from discord import Intents, AllowedMentions, Status, Activity, ActivityType
from discord.ext.commands import Bot

from src.utils.cache import GuildCache


class Plyoox(Bot):
    db: asyncpg.Pool = None
    cache: dict[int, GuildCache] = dict()

    def __init__(self):
        intents = Intents(bans=True, guild_messages=True, guilds=True, members=True)
        allowed_mentions = AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)

        super().__init__(intents=intents, allowed_mentions=allowed_mentions, max_messages=None, command_prefix="+")

    async def setup_hook(self) -> None:
        self.loop.create_task(self._clear_cache())
        self.loop.create_task(self._refresh_presence())

        await self._create_db_pool()

    async def on_ready(self):
        print("Ready")
        print(self.user.id)

    async def _create_db_pool(self):
        self.db = await asyncpg.create_pool(
            database=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USERNAME"),
            password=os.getenv("DATABASE_PASSWORD"),
            host=os.getenv("DATABASE_HOST"),
            port=5432,
        )

    async def _refresh_presence(self):
        while True:
            activity = Activity(name="plyoox.net | /help", type=ActivityType.listening)
            status = Status.online

            await self.change_presence(status=status, activity=activity)
            await asyncio.sleep(60 * 60 * 12)  # 12 hours

    async def _clear_cache(self):
        while True:
            for id, cache in self.cache.items():
                time_diff = datetime.now() - cache["accessed_at"]
                if time_diff.total_seconds() > 86400:  # 24 hours
                    self.cache.pop(id)

            await asyncio.sleep(60 * 60 * 24)  # every 24 hours

    async def get_cache(self, id: int) -> GuildCache:
        cache = self.cache.get(id)

        if not cache:
            pass

        return cache
