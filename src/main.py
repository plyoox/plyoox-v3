from __future__ import annotations

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp
import asyncpg
import discord
from discord import utils
from discord.ext import commands

from cache import CacheManager
from lib import database, extensions

if TYPE_CHECKING:
    from extensions.Timers import Timer
    from extensions.Notification import Notification
    from extensions.Anilist import Anilist

logger = logging.getLogger(__name__)

plugins = [
    "extensions.Infos",
    "extensions.Leveling",
    "extensions.Welcome",
    "extensions.Owner",
    "extensions.Moderation",
    "extensions.Logging",
    "extensions.Fun",
    "extensions.Timers",
    "extensions.Anilist",
    "extensions.DataHandler",
    "extensions.Notification",
    "extensions.Migration",
    "extensions.Statistics",
    "extensions.EmbedCreator",
]


class Plyoox(commands.Bot):
    db: asyncpg.Pool
    cache: CacheManager
    start_time: datetime
    session: aiohttp.ClientSession
    imager_url: str | None

    def __init__(self):
        intents = discord.Intents(
            bans=True,
            message_content=True,
            guild_messages=True,
            guilds=True,
            members=True,
            auto_moderation_execution=True,
            auto_moderation_configuration=True,
        )
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)

        super().__init__(
            intents=intents,
            allowed_mentions=allowed_mentions,
            max_messages=2000,
            command_prefix=commands.when_mentioned,
            tree_cls=extensions.CommandTree,
            chunk_guilds_at_startup=False,
            help_command=None,
        )

        self.imager_url = os.getenv("IMAGER_URL")

    async def setup_hook(self) -> None:
        self.loop.create_task(self._refresh_presence())

        await self.tree.set_translator(extensions.Translator())

        for plugin in plugins:
            logger.debug(f"Load plugin '{plugin}'...")
            await self.load_extension(plugin)

        logger.info("Plugins loaded")

    async def on_ready(self) -> None:
        logger.info("Ready")
        self.start_time = utils.utcnow()

    async def _create_db_pool(self) -> None:
        try:
            self.db = await asyncpg.create_pool(os.getenv("POSTGRES_DSN"), init=database._init_db_connection)
            self.cache = CacheManager(self.db)

        except asyncpg.ConnectionDoesNotExistError:
            logger.critical(f"Could not connect to the database: {traceback.format_exc()}")
            sys.exit(1)

    async def _create_http_client(self) -> None:
        self.session = aiohttp.ClientSession()

    async def _refresh_presence(self) -> None:
        while True:
            if not self.is_ready():
                await asyncio.sleep(30)

            activity = discord.Activity(name="plyoox.net", type=discord.ActivityType.listening)
            status = discord.Status.online

            await self.change_presence(status=status, activity=activity)
            await asyncio.sleep(60 * 60 * 12)  # 12 hours

    @property
    def timer(self) -> Timer | None:
        return self.get_cog("Timer")

    @property
    def notification(self) -> Notification | None:
        return self.get_cog("Notification")

    @property
    def anilist(self) -> Anilist | None:
        return self.get_cog("Anilist")
