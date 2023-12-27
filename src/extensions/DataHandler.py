from __future__ import annotations

import datetime
import logging
import os
import re
import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from main import Plyoox

LOGGING_COLORS = {
    logging.INFO: discord.Color.blue(),
    logging.ERROR: discord.Color.red(),
    logging.WARNING: discord.Color.yellow(),
    logging.CRITICAL: discord.Color.dark_red(),
    logging.DEBUG: discord.Color.dark_gray(),
}

RESUME_REGEX = re.compile(r"Shard ID (\d|None) has successfully RESUMED session.+")


class DiscordNotificationLoggingHandler(logging.Handler):
    def __init__(self, cog: EventHandlerCog):
        self.cog = cog
        super().__init__(logging.INFO)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("tornado."):
            return False

        elif hasattr(record, "message") and RESUME_REGEX.match(record.message):
            return False

        return True

    def emit(self, record: logging.LogRecord) -> None:
        self.cog.add_logging_record(record)


class EventHandlerCog(commands.Cog):
    def __init__(self, bot: Plyoox, webhook: discord.Webhook | None):
        self.bot = bot
        self._logging_data: list[logging.LogRecord] = []
        self._logging_webhook = webhook

        if webhook is not None:
            self.send_logging_data.start()

    def cog_unload(self):
        self.send_logging_data.cancel()

    def add_logging_record(self, record: logging.LogRecord) -> None:
        self._logging_data.append(record)

    @tasks.loop(seconds=60)
    async def send_logging_data(self):
        if not self._logging_data:
            return

        embeds = []
        message_length = 0

        for record in self._logging_data[:10]:
            embed = discord.Embed(
                title=record.name,
                color=LOGGING_COLORS[record.levelno],
                timestamp=datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc),
            )

            if record.exc_info:
                err_type, err_value, err_traceback = record.exc_info
                embed.description = f"{record.message}: ```py\n{''.join(traceback.format_exception(err_type, err_value, err_traceback))}```"
            else:
                embed.description = record.message

            if message_length + len(embed) <= 6000:
                embeds.append(embed)
                self._logging_data.remove(record)
            else:
                break

        await self._logging_webhook.send(embeds=embeds)

    @send_logging_data.before_loop
    async def before_send_logging_data(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.db.execute("INSERT INTO guild_config (id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)

    @app_commands.command(
        name="register-guild",
        description="Registers the guild for the bot. This is only needed when the bot was invited while it was offline.",
    )
    @app_commands.guild_only
    @app_commands.default_permissions(administrator=True)
    async def register_guild(self, interaction: discord.Interaction):
        await self.bot.db.execute(
            "INSERT INTO guild_config (id) VALUES ($1) ON CONFLICT DO NOTHING", interaction.guild_id
        )
        await interaction.response.send_message("Guild registered.", ephemeral=True)


async def setup(bot: Plyoox):
    webhook = None

    webhook_id = os.getenv("LOGGING_WEBHOOK_ID")
    webhook_token = os.getenv("LOGGING_WEBHOOK_TOKEN")

    if webhook_id and webhook_token:
        webhook = discord.Webhook.partial(int(webhook_id), webhook_token, session=bot.session)

    cog = EventHandlerCog(bot, webhook)
    if webhook is not None:
        logging.getLogger().addHandler(DiscordNotificationLoggingHandler(cog))

    await bot.add_cog(cog)
