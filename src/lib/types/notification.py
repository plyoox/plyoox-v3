from datetime import datetime
from typing import TypedDict


class TwitchLiveNotification(TypedDict):
    guild_id: int
    user_id: int
    stream_id: int
    viewer_count: int
    name: str
    title: str
    thumbnail_url: str
    game: str
    started_at: datetime


class TwitchOfflineNotification(TypedDict):
    guild_id: int
    stream_id: int


class YoutubeVideoNotification(TypedDict):
    user_id: str
    video_id: str
