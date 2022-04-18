import asyncio
import logging
import os
import traceback

import asyncpg
from discord import Intents, AllowedMentions, Status, Activity, ActivityType, Message, Object
from discord.ext.commands import Bot

from lib.extensions.command_tree import CommandTree
from src.cache import CacheManager

logger = logging.getLogger(__name__)


plugins = ["plugins.Infos"]


class Plyoox(Bot):
    db: asyncpg.Pool = None
    cache: CacheManager
    test_guild = Object(820727787085234246)

    def __init__(self):
        intents = Intents(bans=True, guild_messages=True, guilds=True, members=True)

        allowed_mentions = AllowedMentions(
            everyone=False, users=True, roles=False, replied_user=True
        )

        super().__init__(
            intents=intents,
            allowed_mentions=allowed_mentions,
            max_messages=None,
            command_prefix=[],
            tree_cls=CommandTree,
        )

    async def setup_hook(self) -> None:
        self.loop.create_task(self._refresh_presence())

        for plugin in plugins:
            await self.load_extension(plugin)

    async def on_ready(self) -> None:
        print("Ready")
        print(self.user.id)

        # await self.tree.sync(guild=Object(820727787085234246))

    async def on_message(self, message: Message, /) -> None:
        pass

    async def _create_db_pool(self) -> None:
        try:
            self.db = await asyncpg.create_pool(
                database=os.getenv("DATABASE_NAME"),
                password=os.getenv("DATABASE_PASSWORD"),
                user=os.getenv("DATABASE_USERNAME"),
                host=os.getenv("DATABASE_HOST"),
                port=5432,
            )
        except asyncpg.ConnectionDoesNotExistError:
            logger.error(f"Could not connect to the database: {traceback.format_exc()}")
            exit(-1)

    async def _refresh_presence(self) -> None:
        while True:
            if not self.is_ready():
                await asyncio.sleep(30)

            activity = Activity(name="plyoox.net | /help", type=ActivityType.listening)
            status = Status.online

            await self.change_presence(status=status, activity=activity)
            await asyncio.sleep(60 * 60 * 12)  # 12 hours
