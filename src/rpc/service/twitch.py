from __future__ import annotations

from typing import TYPE_CHECKING

from rpc.generated.twitch_pb2 import TwitchLiveNotification, TwitchOfflineNotification, Empty
from rpc.generated.twitch_pb2_grpc import TwitchNotificationServicer


if TYPE_CHECKING:
    from main import Plyoox


class TwitchService(TwitchNotificationServicer):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    def LiveNotification(self, request: TwitchLiveNotification, context):
        print("online", request.name, request.stream_id)

        return Empty()

    def OfflineNotification(self, request: TwitchOfflineNotification, context):
        print("offline", request.stream_id)

        return Empty()
