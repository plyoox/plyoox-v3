from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class YoutubeNotification(_message.Message):
    __slots__ = ("user_id", "video_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    VIDEO_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    video_id: str
    def __init__(self, user_id: _Optional[str] = ..., video_id: _Optional[str] = ...) -> None: ...

class AddYoutubeNotification(_message.Message):
    __slots__ = ("youtube_url", "guild_id", "channel_id")
    YOUTUBE_URL_FIELD_NUMBER: _ClassVar[int]
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_ID_FIELD_NUMBER: _ClassVar[int]
    youtube_url: str
    guild_id: int
    channel_id: int
    def __init__(self, youtube_url: _Optional[str] = ..., guild_id: _Optional[int] = ..., channel_id: _Optional[int] = ...) -> None: ...

class RemoveYoutubeNotification(_message.Message):
    __slots__ = ("youtube_id", "guild_id")
    YOUTUBE_ID_FIELD_NUMBER: _ClassVar[int]
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    youtube_id: str
    guild_id: int
    def __init__(self, youtube_id: _Optional[str] = ..., guild_id: _Optional[int] = ...) -> None: ...

class YouTubeUser(_message.Message):
    __slots__ = ("id", "name", "profile_image_url")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROFILE_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    profile_image_url: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., profile_image_url: _Optional[str] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
