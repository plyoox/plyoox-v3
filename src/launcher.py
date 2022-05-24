import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

from main import Plyoox

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--generate-db", action=argparse.BooleanOptionalAction)
args = parser.parse_args()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


async def generate_db():
    import sqlalchemy.ext.asyncio as async_sql

    import lib.database as db

    dns = os.getenv("POSTGRES").replace("postgresql://", "postgresql+asyncpg://")
    engine = async_sql.create_async_engine(dns)

    async with engine.begin() as conn:
        print("Setup Database")
        logger.info("Setup database")
        await conn.run_sync(db.metadata.drop_all)
        await conn.run_sync(db.metadata.create_all)


async def main():
    bot = Plyoox()

    await bot._create_db_pool()
    await bot._create_http_client()

    async with bot:
        await bot.start(os.getenv("TOKEN"))


if args.generate_db:
    asyncio.run(generate_db())
else:
    asyncio.run(main())
