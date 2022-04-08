import os
import asyncio
import asyncpg

from dotenv import load_dotenv

from main import Plyoox

load_dotenv()


async def main():
    bot = Plyoox()

    async with bot:
        await bot.start(os.getenv("TOKEN"))


asyncio.run(main())
