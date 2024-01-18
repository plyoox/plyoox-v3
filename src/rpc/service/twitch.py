from __future__ import annotations

from typing import TYPE_CHECKING
import datetime

from rpc.generated.twitch_pb2 import TwitchLiveNotification, TwitchOfflineNotification, Empty
from rpc.generated.twitch_pb2_grpc import TwitchNotificationServicer


if TYPE_CHECKING:
    from main import Plyoox

    from lib.types import TwitchLiveNotification as TwitchLiveNotificationType


class TwitchService(TwitchNotificationServicer):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def LiveNotification(self, request: TwitchLiveNotification, context):
        notification = self.bot.notification

        data: TwitchLiveNotificationType = {
            "game": request.game,
            "name": request.name,
            "title": request.title,
            "viewer_count": request.viewer_count,
            "user_id": request.user_id,
            "thumbnail_url": request.thumbnail_url,
            "guild_id": request.guild_id,
            "started_at": datetime.datetime.fromtimestamp(request.started_at),
            "stream_id": request.stream_id,
        }

        await notification.send_twitch_notification(data)

        return Empty()

    async def OfflineNotification(self, request: TwitchOfflineNotification, context):
        print("offline", request.stream_id)

        return Empty()
