from __future__ import annotations

from typing import TYPE_CHECKING

import grpc

from rpc.generated import cache_pb2_grpc, twitch_pb2_grpc
from rpc.service import TwitchService, UpdateCacheService

if TYPE_CHECKING:
    from main import Plyoox


async def start_server(bot: Plyoox, url: str) -> grpc.aio.Server:
    server = grpc.aio.server()

    cache_pb2_grpc.add_UpdateCacheServicer_to_server(UpdateCacheService(bot), server)
    twitch_pb2_grpc.add_TwitchNotificationServicer_to_server(TwitchService(bot), server)

    server.add_insecure_port(url)

    await server.start()

    return server
