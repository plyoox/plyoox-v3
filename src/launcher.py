import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--generate-db", action="store_true", help="Generate database")
group.add_argument("--sync-commands", action="store_true", help="Sync commands with discord")
args = parser.parse_args()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


async def generate_db():
    import sqlalchemy.ext.asyncio as async_sql

    import lib.database as db

    # Create database engine
    engine = async_sql.create_async_engine(os.getenv("POSTGRES").replace("postgresql://", "postgresql+asyncpg://"))

    async with engine.begin() as conn:
        logger.debug("Setup database...")
        await conn.run_sync(db.metadata.drop_all)
        await conn.run_sync(db.metadata.create_all)
        logger.info("Database set up")


async def main():
    import web_server
    from main import Plyoox

    bot = Plyoox(sync_commands=args.sync_commands)

    await bot._create_db_pool()
    await bot._create_http_client()

    await web_server.start_webserver(bot)

    async with bot:
        await bot.start(os.getenv("TOKEN"))


if args.generate_db:
    asyncio.run(generate_db())
else:
    asyncio.run(main())
