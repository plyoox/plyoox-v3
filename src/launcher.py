import asyncio
import logging
import os
import sys

import discord

from rpc.grpc_server import start_server

if sys.platform == "linux":
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Set up logging
logger = logging.getLogger()
discord.utils.setup_logging(root=True, level=logging.INFO)

logging.getLogger("tornado.access").setLevel(logging.ERROR)


async def main():
    import signal
    import yarl

    from main import Plyoox

    compress = True
    shard_count = None
    if gateway_host := os.getenv("GATEWAY_HOST"):
        import aiohttp
        from discord.gateway import DiscordWebSocket

        logger.info(f"Using own gateway: {gateway_host}")
        DiscordWebSocket.DEFAULT_GATEWAY = yarl.URL(f"ws://{gateway_host}")

        compress = False

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{gateway_host}/shard-count") as response:
                if not response.ok:
                    raise Exception("Failed getting shard count")

                response_text = await response.text()

                shard_count = int(response_text)

    bot = Plyoox(compress, shard_count=shard_count)

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
