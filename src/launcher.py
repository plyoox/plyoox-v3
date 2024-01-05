import argparse
import asyncio
import logging
import os
import sys

import discord
from dotenv import load_dotenv

from rpc.grpc_server import start_server

if sys.platform == "linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--prod", action="store_true", help="Sync commands with discord")
args = parser.parse_args()

# Set up logging

logger = logging.getLogger()
discord.utils.setup_logging(root=True, level=logging.DEBUG)

logging.getLogger("tornado.access").setLevel(logging.ERROR)


async def main():
    import signal
    import yarl

    from main import Plyoox

    if gateway_url := os.getenv("GATEWAY_URL"):
        from discord.gateway import DiscordWebSocket

        logger.info(f"Using own gateway url: {gateway_url}")
        DiscordWebSocket.DEFAULT_GATEWAY = yarl.URL(gateway_url)

    bot = Plyoox()

    await bot._create_db_pool()
    await bot._create_http_client()

    async with bot:
        if sys.platform == "linux":
            bot.loop.add_signal_handler(signal.SIGTERM, lambda: bot.loop.create_task(bot.close()))

        server = await start_server(bot, "[::]:50051")

        try:
            await asyncio.gather(server.wait_for_termination(), bot.start(os.getenv("DISCORD_TOKEN")))
        finally:
            await server.stop(grace=1)
            await bot.close()


asyncio.run(main())
