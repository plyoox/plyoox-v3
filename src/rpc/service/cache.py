from __future__ import annotations

from typing import TYPE_CHECKING

from rpc.generated.cache_pb2 import Empty, Id

from rpc.generated.cache_pb2_grpc import UpdateCacheServicer

if TYPE_CHECKING:
    from main import Plyoox


class UpdateCacheService(UpdateCacheServicer):
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

    def DeleteModerationPunishmentCache(self, request, context):
        self.bot.cache.remove_cache(request.id, "punishment")

        return Empty()
