import asyncio
import logging
import os

from dotenv import load_dotenv

from main import Plyoox

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger("discord.gateway").setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


async def main():
    bot = Plyoox()

    await bot._create_db_pool()
    await bot._create_http_client()

    async with bot:
        await bot.start(os.getenv("TOKEN"))


asyncio.run(main())
