import argparse
import asyncio
import logging
import os
import sys

import discord
from dotenv import load_dotenv

if sys.platform == "linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--generate-db", action="store_true", help="Generate database")
group.add_argument("--prod", action="store_true", help="Sync commands with discord")
args = parser.parse_args()

# Set up logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
discord.utils.setup_logging(root=True)

logging.getLogger("tornado.access").setLevel(logging.ERROR)


async def generate_db():
    import sqlalchemy.ext.asyncio as async_sql

    import lib.database as db

    # Create database engine
    engine = async_sql.create_async_engine(
        os.getenv("POSTGRES_DSN").replace("postgresql://", "postgresql+asyncpg://")
    )

    async with engine.begin() as conn:
        logger.debug("Setup database...")
        await conn.run_sync(db.metadata.drop_all)
        await conn.run_sync(db.metadata.create_all)
        logger.info("Database set up")


async def main():
    import signal
    import yarl

    import web_server
    from main import Plyoox

    if gateway_url := os.getenv("GATEWAY_URL"):
        from discord.gateway import DiscordWebSocket

        logger.info(f"Using own gateway url: {gateway_url}")
        DiscordWebSocket.DEFAULT_GATEWAY = yarl.URL(gateway_url)

    bot = Plyoox()

    await bot._create_db_pool()
    await bot._create_http_client()
    await web_server.start_webserver(bot)

    async with bot:
        if sys.platform == "linux":
            bot.loop.add_signal_handler(
                signal.SIGTERM, lambda: bot.loop.create_task(bot.close())
            )
        await bot.start(os.getenv("DISCORD_TOKEN"))


if args.generate_db:
    asyncio.run(generate_db())
else:
    asyncio.run(main())
