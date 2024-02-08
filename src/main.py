from __future__ import annotations

import asyncio
import copy
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

import translation
from cache import CacheManager
from lib import database, extensions
from lib.message_cache import MessageCache

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
    "extensions.Statistics",
]


class Plyoox(commands.AutoShardedBot):
    db: asyncpg.Pool
    cache: CacheManager
    start_time: datetime
    session: aiohttp.ClientSession
    imager_url: str
    notificator_url: str

    def __init__(self, compress: bool = True):
        intents = discord.Intents(
            moderation=True,
            message_content=True,
            guild_messages=True,
            guilds=True,
            members=True,
            auto_moderation_execution=True,
            webhooks=True,
        )
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)

        super().__init__(
            intents=intents,
            allowed_mentions=allowed_mentions,
            max_messages=None,
            command_prefix=commands.when_mentioned,
            tree_cls=extensions.CommandTree,
            chunk_guilds_at_startup=False,
            help_command=None,
            compress=compress,
        )

        self.messages = MessageCache[discord.Message](max_length=2500)
        self.presence_task = None
        self.imager_url = os.getenv("IMAGER_URL")

        if self.imager_url is None:
            plugins.remove("extensions.Leveling")
            plugins.remove("extensions.Anilist")
            logger.warning("IMAGER_URL is not set. Level and Anilist extension will not be loaded.")

    async def setup_hook(self) -> None:
        await self.tree.set_translator(translation.Translator())

        for plugin in plugins:
            logger.debug(f"Load plugin '{plugin}'...")
            await self.load_extension(plugin)

        logger.info("Plugins loaded")

        self.presence_task = self.loop.create_task(self._update_status_task())

    async def on_ready(self) -> None:
        logger.info("Ready")
        self.start_time = utils.utcnow()

    async def _create_db_pool(self) -> None:
        try:
            self.db = await asyncpg.create_pool(os.getenv("POSTGRES_DSN"), init=database._init_db_connection)
            self.cache = CacheManager(self.db)
        except asyncpg.ConnectionDoesNotExistError:
            logger.critical(f"Could not connect to the database: {traceback.format_exc()}")
            sys.exit(-1)
        except ConnectionRefusedError:
            logger.critical("Remote computer refused the connection")
            sys.exit(-2)

    async def _create_http_client(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close(self):
        logger.info("Stopping bot...")
        await self.session.close()
        await self.db.close()

        await super().close()
        logger.info("Plyoox has been successfully stopped.")

    @property
    def timer(self) -> Timer | None:
        return self.get_cog("Timer")

    @property
    def notification(self) -> Notification | None:
        return self.get_cog("Notification")

    @property
    def anilist(self) -> Anilist | None:
        return self.get_cog("Anilist")

    async def _update_status_task(self):
        await asyncio.sleep(30)

        while not self.is_closed():
            await self.change_presence(activity=discord.CustomActivity(name="plyoox.net"))
            await asyncio.sleep(43200)

    # Message cache events

    async def on_message(self, message: discord.Message):
        await self.process_commands(message)

        # Only cache messages of guilds when the moderation or the logging
        # module is enabled.
        if await self.cache.get_logging(message.guild.id):
            self.messages.add_item(message)
            return

        mod_cache = await self.cache.get_moderation(message.guild.id)
        if mod_cache is not None and mod_cache.active:
            self.messages.add_item(message)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        message = self.messages.get_item(payload.message_id)

        if message is not None:
            before_message = copy.copy(message)
            payload.cached_message = before_message

            message._update(payload.data)

            self.dispatch("custom_message_edit", before_message, message)

        self.dispatch("custom_raw_message_edit", payload)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        message = self.messages.remove_item(payload.message_id)

        if message is not None:
            payload.cached_message = message

        self.dispatch("custom_raw_message_delete", payload)

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        messages = []

        for message_id in payload.message_ids:
            deleted_message = self.messages.remove_item(message_id)
            if deleted_message:
                messages.append(deleted_message)

        payload.cached_messages = messages

        self.dispatch("custom_raw_bulk_message_delete", payload)
