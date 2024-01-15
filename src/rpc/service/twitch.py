from __future__ import annotations

from typing import TYPE_CHECKING

from rpc.generated.twitch_pb2_grpc import TwitchNotificationServicer


if TYPE_CHECKING:
    from main import Plyoox


class TwitchService(TwitchNotificationServicer):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    def LiveNotification(self, request, context):
        pass

    def OfflineNotification(self, request, context):
        pass
