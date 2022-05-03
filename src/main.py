import asyncio
import logging
import os
import traceback
from datetime import datetime

import asyncpg
import discord
from discord import utils
from discord.ext import commands

from lib.extensions.command_tree import CommandTree
from src.cache import CacheManager

logger = logging.getLogger(__name__)


plugins = ["plugins.Infos", "plugins.Leveling", "plugins.Welcome", "plugins.Owner", "plugins.Moderation"]


class Plyoox(commands.Bot):
    db: asyncpg.Pool = None
    cache: CacheManager
    test_guild = discord.Object(505438986672537620)
    start_time: datetime

    def __init__(self):
        intents = discord.Intents(bans=True, guild_messages=True, guilds=True, members=True)

        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)

        super().__init__(
            intents=intents,
            allowed_mentions=allowed_mentions,
            max_messages=None,
            command_prefix=[],
            tree_cls=CommandTree,
            owner_id=263347878150406144,
        )

    async def setup_hook(self) -> None:
        self.loop.create_task(self._refresh_presence())

        for plugin in plugins:
            print("Loaded plugin", plugin, end="\r")
            await asyncio.sleep(1)
            await self.load_extension(plugin)

    async def on_ready(self) -> None:
        print("Ready")
        print(self.user.id)

        self.start_time = utils.utcnow()

        self.tree.copy_global_to(guild=self.test_guild)
        await self.tree.sync(guild=self.test_guild)

    async def on_message(self, message: discord.Message) -> None:
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
            self.cache = CacheManager(self.db)

        except asyncpg.ConnectionDoesNotExistError:
            logger.error(f"Could not connect to the database: {traceback.format_exc()}")
            exit(-1)

    async def _refresh_presence(self) -> None:
        while True:
            if not self.is_ready():
                await asyncio.sleep(30)

            activity = discord.Activity(name="plyoox.net | /help", type=discord.ActivityType.listening)
            status = discord.Status.online

            await self.change_presence(status=status, activity=activity)
            await asyncio.sleep(60 * 60 * 12)  # 12 hours
