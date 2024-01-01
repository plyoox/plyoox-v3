from __future__ import annotations

from typing import TYPE_CHECKING

import grpc

from rpc.generated import cache_pb2_grpc
from rpc.generated.cache_pb2_grpc import UpdateCacheServicer
from rpc.generated.cache_pb2 import Id, Empty


if TYPE_CHECKING:
    from main import Plyoox


class UpdateCacheServicer(UpdateCacheServicer):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    def DeleteModerationCache(self, request: Id, context):
        self.bot.cache.remove_cache(request.id, "mod")

        return Empty()

    def DeleteAutoModerationCache(self, request: Id, context):
        self.bot.cache.remove_cache(request.id, "automod")

        return Empty()

    def DeleteWelcomeCache(self, request: Id, context):
        self.bot.cache.remove_cache(request.id, "wel")

        return Empty()

    def DeleteLoggingCache(self, request: Id, context):
        self.bot.cache.remove_cache(request.id, "log")

        return Empty()

    def DeleteLevelCache(self, request: Id, context):
        self.bot.cache.remove_cache(request.id, "lvl")

        return Empty()


async def start_server(bot: Plyoox, url: str) -> grpc.aio.Server:
    server = grpc.aio.server()
    cache_pb2_grpc.add_UpdateCacheServicer_to_server(UpdateCacheServicer(bot), server)

    server.add_insecure_port(url)

    await server.start()

    return server
