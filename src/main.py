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
    from plugins.Timers import Timer
    from plugins.Notification import Notification
    from plugins.Anilist import Anilist

logger = logging.getLogger(__name__)

plugins = [
    "plugins.Infos",
    "plugins.Leveling",
    "plugins.Welcome",
    "plugins.Owner",
    "plugins.Moderation",
    "plugins.Logging",
    "plugins.Fun",
    "plugins.Timers",
    "plugins.Anilist",
    "plugins.DataHandler",
    "plugins.Notification",
    "plugins.Migration",
]


class Plyoox(commands.Bot):
    db: asyncpg.Pool = None
    cache: CacheManager
    start_time: datetime
    session: aiohttp.ClientSession

    def __init__(self, *, sync_commands: bool = False):
        intents = discord.Intents(bans=True, message_content=True, guild_messages=True, guilds=True, members=True)
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)
        self.sync_commands = sync_commands

        super().__init__(
            intents=intents,
            allowed_mentions=allowed_mentions,
            max_messages=2000,
            command_prefix=[],
            tree_cls=extensions.CommandTree,
            application_id=int(os.getenv("CLIENT_ID")),
            owner_id=int(os.getenv("OWNER_ID")),
        )

    async def setup_hook(self) -> None:
        self.loop.create_task(self._refresh_presence())

        await self.tree.set_translator(extensions.Translator())

        for plugin in plugins:
            logger.debug(f"Load plugin '{plugin}'...")
            await self.load_extension(plugin)

        logger.info("Plugins loaded")

        if self.sync_commands:
            # Sync commands with discord
            logger.debug("Sync commands with discord...")

            await self.tree.sync()

            if owner_guild_id := os.getenv("OWNER_GUILD"):
                owner_guild = discord.Object(int(owner_guild_id))
                await self.tree.sync(guild=owner_guild)

            await self.close()
            logger.info("Commands successfully synced")
            sys.exit(0)

    async def on_ready(self) -> None:
        logger.info("Ready")
        self.start_time = utils.utcnow()

    async def on_message(self, message: discord.Message) -> None:
        pass

    async def _create_db_pool(self) -> None:
        try:
            self.db = await asyncpg.create_pool(os.getenv("POSTGRES"), init=database._init_db_connection)
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

            activity = discord.Activity(name="plyoox.net | /help", type=discord.ActivityType.listening)
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
