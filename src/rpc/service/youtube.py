from __future__ import annotations

from typing import TYPE_CHECKING

from rpc.generated.youtube_pb2 import Empty, YoutubeNotification
from rpc.generated.youtube_pb2_grpc import YoutubeServicer


if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import YoutubeVideoNotification


class YoutubeService(YoutubeServicer):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def VideoPublish(self, request: YoutubeNotification, context):
        notification = self.bot.notification

        data: YoutubeVideoNotification = {
            "user_id": request.user_id,
            "video_id": request.video_id,
        }

        await notification.send_youtube_notification(data)

        return Empty()
